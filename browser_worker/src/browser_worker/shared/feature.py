from collections.abc import Sequence
from dataclasses import dataclass

from dishka import Provider
from fastapi import APIRouter

from browser_worker.presentation.api_errors import ApiErrorSpec


@dataclass(frozen=True, slots=True)
class Feature:
    name: str
    routers: Sequence[APIRouter] = ()
    providers: Sequence[type[Provider]] = ()
    api_errors: Sequence[ApiErrorSpec] = ()
