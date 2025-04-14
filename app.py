from rekuest_next.actors.functional import ThreadedFuncActor
from rekuest_next.api.schema import TemplateInput, DefinitionInput, PortInput, PortKind, PortScope, NodeKind
from rekuest_next.structures.default import get_default_structure_registry
from album.api import Album
from rekuest_next.definition.registry import (
    get_default_definition_registry,
)
from functools import partial

# Create the Album instance and load its collection.
album = Album.Builder().build()
album.load_or_create_collection()

class BlaBla(ThreadedFuncActor):
    pass


def register_all_solutions():

    # Retrieve the album index as a dictionary.
    index = album.get_index_as_dict()

    # Iterate over each catalog in the index.
    for catalog in index.get("catalogs", []):
        # Each catalog has a list of solutions.
        for sol in catalog.get("solutions", []):
            setup = sol.get("setup", {})
            group = setup.get("group", "album")
            name = setup.get("name")
            version = setup.get("version")
            if not name or not version:
                # Skip invalid solution entries.
                continue

            # Create a unique solution identifier.
            solution_id = f"{group}:{name}:{version}"

            # Get the argument definitions for the solution.
            # For instance, template-imagej2 defines an argument named 'output_image_path'
            # and template-napari defines one named 'input_image_path'.
            solution_args = []
            arg_defs = setup.get("args", [])
            for arg_def in arg_defs:
                arkitekt_arg = PortInput(key=arg_def["name"], description=arg_def["description"], kind=PortKind.STRING, scope=PortScope.LOCAL, nullable=False)
                solution_args.append(arkitekt_arg)

            definition = DefinitionInput(
                                                                            name=solution_id,
                                                                            args=solution_args,
                                                                            returns=[],
                                                                            collections=[],
                                                                            stateful=False,
                                                                            portGroups=[],
                                                                            kind=NodeKind.FUNCTION,
                                                                            isTestFor=[],
                                                                            interfaces=[],
                                                                            isDev=True
                                                                        )
            get_default_definition_registry().register_at_interface(solution_id,
                                                                    TemplateInput(
                                                                        definition=definition,
                                                                        dependencies=[],
                                                                        interface=solution_id,
                                                                        dynamic=False
                                                                    ),
                                                                    structure_registry=get_default_structure_registry(),
                                                                    actorBuilder=partial(BlaBla, assign=partial(album.run, solution_id), structure_registry=get_default_structure_registry(), definition=definition))


register_all_solutions()