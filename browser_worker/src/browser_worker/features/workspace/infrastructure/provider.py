from dishka import Provider, Scope, provide

from browser_worker.features.workspace.application.workspace import Workspace
from browser_worker.features.workspace.infrastructure.settings import WorkspaceSettings


class WorkspaceProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> WorkspaceSettings:
        return WorkspaceSettings()

    @provide(scope=Scope.APP)
    def workspace(self, settings: WorkspaceSettings) -> Workspace:
        return Workspace(settings.path.resolve())
