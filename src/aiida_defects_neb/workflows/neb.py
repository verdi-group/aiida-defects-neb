"""Work chain to calculate the transition barrier via a NEB calculation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiida import engine, orm
from aiida_quantumespresso.workflows.protocols.utils import ProtocolMixin
from aiida_vasp.workchains.v2.vasp import VaspWorkChain, potential_family_validator
from aiida_vasp.workchains.neb import VaspNEBWorkChain


if TYPE_CHECKING:
    from plumpy import WorkChainSpec


class NebWorkChain(engine.WorkChain, ProtocolMixin):
    """Work chain to calculate the transition barrier via a NEB calculation."""

    @classmethod
    def define(cls, spec: WorkChainSpec) -> None:
        super().define(spec)

        spec.expose_inputs(
            process_class=VaspWorkChain,
            exclude=("structure", "potential_family", "potential_mapping"),
            namespace="relax",
        )
        spec.expose_inputs(
            process_class=VaspNEBWorkChain,
            exclude=("initial_structure", "final_structure", "neb_images", "potential_family", "potential_mapping"),
            namespace="neb",
        )
        spec.input(
            "initial_structure",
            valid_type=orm.StructureData,
            required=True,
        )
        spec.input(
            "final_structure",
            valid_type=orm.StructureData,
            required=True,
        )
        spec.input(
            "number_images",
            valid_type=orm.Int,
            required=True
        )
        spec.input(
            "potential_family",
            valid_type=orm.Str,
            required=True,
            validator=potential_family_validator,
        )
        spec.input(
            "potential_mapping",
            valid_type=orm.Dict,
            required=True,
        )

        spec.outline(cls.relax, cls.neb, cls.neb_ci, cls.assign_outputs)

        spec.output(
            "energies",
            valid_type=orm.List,
            required=True
        )
        spec.output_namespace(
            'structures',
            valid_type=orm.StructureData,
            dynamic=True
        )

    @classmethod
    def get_protocol_filepath(cls):
        """Return ``pathlib.Path`` to the ``.yaml`` file that defines the protocols."""
        from importlib_resources import files

        from aiida_defects_neb.workflows import protocols

        return files(protocols) / "neb.yaml"

    @classmethod
    def get_builder_from_protocol(
        cls,
        initial_structure: orm.StructureData,
        final_structure: orm.StructureData,
        vasp_code: orm.Code,
        options: dict | orm.Dict,
        number_images: int = 4,
        overrides=None,
    ):
        """Get a fully populated builder based on the protocol."""
        inputs = cls.get_protocol_inputs(protocol="default", overrides=overrides)

        builder = cls.get_builder()

        builder.potential_family = inputs["potential_family"]

        if "potential_mapping" in inputs:
            builder.potential_mapping = inputs["potential_mapping"]
        else:
            builder.potential_mapping = {element: element for element in initial_structure.get_symbols_set()}

        kpoints = orm.KpointsData()
        kpoints.set_kpoints_mesh([2, 2, 2])

        relax_inputs = {"code": vasp_code, "kpoints": kpoints, "options": options}
        relax_inputs.update(inputs["relax"])

        neb_inputs = {"code": vasp_code, "kpoints": kpoints, "options": options}
        neb_inputs.update(inputs["neb"])
        neb_inputs['parameters']['incar']['images'] = number_images

        builder.initial_structure = initial_structure
        builder.final_structure = final_structure
        builder.relax = relax_inputs
        builder.neb = neb_inputs
        builder.number_images = number_images

        return builder

    def relax(self) -> engine.ExitCode | None:
        """Relax the geometry of the initial and final structure."""

        processes_to_run = {}

        for structure_label in (
            'initial',
            'final'
        ):
            inputs = self.exposed_inputs(VaspWorkChain, "relax")
            inputs["structure"] = self.inputs[f'{structure_label}_structure']
            inputs["potential_family"] = self.inputs.potential_family
            inputs["potential_mapping"] = self.inputs.potential_mapping

            processes_to_run[f'relax_{structure_label}'] = self.submit(VaspWorkChain, inputs)

        return processes_to_run

    def neb(self) -> engine.ExitCode | None:
        """Run the first NEB calculation without the climbing image modification."""

        initial_structure = self.ctx[f'relax_initial'].outputs.structure
        final_structure = self.ctx[f'relax_final'].outputs.structure

        number_images = self.inputs.number_images.value

        neb_images = initial_structure.get_pymatgen().interpolate(final_structure.get_pymatgen(), nimages=number_images)
        images_structure_data = [orm.StructureData(pymatgen=image) for image in neb_images]

        inputs = self.exposed_inputs(VaspNEBWorkChain, "neb")

        inputs["initial_structure"] = initial_structure
        inputs["final_structure"] = final_structure
        inputs["potential_family"] = self.inputs.potential_family
        inputs["potential_mapping"] = self.inputs.potential_mapping
        inputs["neb_images"] = {
            f'image_0{index}': structure_data for index, structure_data in enumerate(images_structure_data[0:-1])
        }
        return {"neb": self.submit(VaspNEBWorkChain, inputs)}

    def neb_ci(self) -> engine.ExitCode | None:
        """Run the NEB calculation with the climbing image modification."""

        initial_structure = self.ctx[f'relax_initial'].outputs.structure
        final_structure = self.ctx[f'relax_final'].outputs.structure

        inputs = self.exposed_inputs(VaspNEBWorkChain, "neb")

        inputs["initial_structure"] = initial_structure
        inputs["final_structure"] = final_structure
        inputs["potential_family"] = self.inputs.potential_family
        inputs["potential_mapping"] = self.inputs.potential_mapping
        inputs["neb_images"] = self.ctx[f'neb'].outputs.structure

        parameters = inputs['parameters'].get_dict()
        parameters['incar']['lclimb'] = True
        inputs['parameters'] = orm.Dict(parameters)

        return {"neb_ci": self.submit(VaspNEBWorkChain, inputs)}

    def assign_outputs(self) -> engine.ExitCode | None:
        """Assign the outputs of the workflow."""
        energies = gather_energies(
            initial_misc=self.ctx[f'relax_initial'].outputs.misc,
            final_misc=self.ctx[f'relax_final'].outputs.misc,
            neb_misc=self.ctx[f'neb'].outputs.misc,
        )
        self.out('energies', energies)
        structures = {
            'initial': self.ctx[f'relax_initial'].outputs.structure,
            'final': self.ctx[f'relax_final'].outputs.structure,
        }
        structures.update(dict(self.ctx['neb_ci'].outputs.structure))
        self.out('structures', structures)


@engine.calcfunction
def gather_energies(initial_misc, final_misc, neb_misc):

    energies = [
    initial_misc.get_dict()['total_energies']['energy_extrapolated']
    ]
    energies.extend([val['energy_extrapolated'] for val in neb_misc.get_dict()['total_energies'].values()])
    energies.append(final_misc.get_dict()['total_energies']['energy_extrapolated'])

    return orm.List(energies)
