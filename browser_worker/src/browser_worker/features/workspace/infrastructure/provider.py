from dishka import Provider, Scope, provide

from browser_worker.features.workspace.application import Workspace
from browser_worker.features.workspace.infrastructure.filesystem import (
    FilesystemWorkspace,
)
from browser_worker.features.workspace.infrastructure.settings import WorkspaceSettings


class WorkspaceProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> WorkspaceSettings:
        return WorkspaceSettings()

    @provide(scope=Scope.APP)
    def workspace(self, settings: WorkspaceSettings) -> Workspace:
        return FilesystemWorkspace(settings.path.resolve())
