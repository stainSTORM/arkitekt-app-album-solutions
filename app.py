from typing import Dict, List
from rekuest_next.actors.functional import FunctionalThreadedFuncActor
from rekuest_next.api.schema import (
    ImplementationInput,
    DefinitionInput,
    PortInput,
    PortKind,
    ActionKind,
)
from arkitekt_next import progress
from rekuest_next.structures.default import get_default_structure_registry
from album.api import Album
from rekuest_next.definition.registry import (
    get_default_definition_registry,
)
from rekuest_next.agents.registry import get_default_extension_registry
from rekuest_next.agents.extension import BaseAgentExtension
from rekuest_next.agents.base import BaseAgent
from koil import run_spawned

from functools import partial


extension_registry = get_default_extension_registry()


class AlbumExtension:
    cleanup: bool = True

    def __init__(self):
        # Create the Album instance and load its collection.
        self.album = Album.Builder().build()

        self.definition_map: Dict[str, DefinitionInput] = {}

    def get_name(self) -> str:
        """Get the name of the extension. This is used to identify the extension
        in the registry."""
        return "album"

    def load_all_solutions(self):
        self.album.load_or_create_collection()
        self.index = self.album.get_index_as_dict()  # type: ignore

    async def astart(self, instance_id: str) -> None:
        """This should be called when the agent starts"""
        # Load the album collection.
        return await run_spawned(self.load_all_solutions)

    async def atear_down(self) -> None:
        """This should be called when the agent is torn down"""
        # Tear down the album collection.
        pass

    async def aget_implementations(self) -> List[ImplementationInput]:
        """Get the implementations for this extension. This
        will be called when the agent starts and will
        be used to register the implementations on the rekuest server
        the implementations in the registry.
        Returns:
            List[ImplementationInput]: The implementations for this extension.
        """
        implementations: List[ImplementationInput] = []

        # Iterate over each catalog in the index.
        for catalog in self.index.get("catalogs", []):  # type: ignore
            # Each catalog has a list of solutions.
            for sol in catalog.get("solutions", []):  # type: ignore
                setup = sol.get("setup", {})  # type: ignore
                group = setup.get("group", "album")  # type: ignore
                name = setup.get("name")  # type: ignore
                version = setup.get("version")  # type: ignore
                if not name or not version:
                    # Skip invalid solution entries.
                    continue

                # Create a unique solution identifier.
                solution_id = f"{group}:{name}:{version}"

                # Get the argument definitions for the solution.
                # For instance, template-imagej2 defines an argument named 'output_image_path'
                # and template-napari defines one named 'input_image_path'.
                solution_args: list[PortInput] = []

                arg_defs = setup.get("args", [])  # type: ignore
                for arg_def in arg_defs:  # type: ignore
                    arkitekt_arg = PortInput(
                        key=arg_def["name"],  # type: ignore
                        description=arg_def["description"],  # type: ignore
                        kind=PortKind.STRING,
                        nullable=False,
                    )
                    solution_args.append(arkitekt_arg)

                definition = DefinitionInput(
                    name=solution_id,
                    args=tuple(solution_args),
                    returns=(),
                    collections=(),
                    stateful=False,
                    portGroups=(),
                    kind=ActionKind.FUNCTION,
                    isTestFor=(),
                    interfaces=(),
                    isDev=True,
                )

                implementations.append(
                    ImplementationInput(
                        definition=definition,
                        dependencies=(),
                        interface=solution_id,
                        dynamic=False,
                    )
                )

                self.definition_map[solution_id] = definition

        return implementations

    async def aspawn_actor_for_interface(
        self,
        agent: "BaseAgent",
        interface: str,
    ) -> FunctionalThreadedFuncActor:
        """This should create an actor from a implementation and return it.

        The actor should not be started!
        """
        # Get the implementation for the interface.
        implementation = await self.aget_implementations()
        for impl in implementation:
            if impl.interface == interface:
                break
        else:
            raise ValueError(f"No implementation found for interface {interface}")

        def assign(**kwargs):  # type: ignore
            progress(0, "Starting album solution")
            if not self.album.is_installed(interface):
                progress(50, "Installing album solution")
                self.album.install(interface)

            progress(70, "Running album solution")
            answer = self.album.run(
                interface,
                argv=kwargs,
            )
            progress(100, "Album solution finished")
            print(answer)
            return answer

        # Create the actor.
        return FunctionalThreadedFuncActor(
            agent=agent,
            assign=assign,  # type: ignore
            structure_registry=get_default_structure_registry(),
            definition=impl.definition,
        )


extension_registry.register(AlbumExtension())
