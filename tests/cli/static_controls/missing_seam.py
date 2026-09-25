"""mypy --strict control: an incomplete authority bundle is refused where it is written.

D-IMPL-353 §4 rule 6. Three shapes an embedder could hand the CLI's in-process
leg, each of which used to sail through behind an arg-type suppression comment, each
now a mypy error on the marked line. No suppression anywhere in this file — the
sibling test asserts that, and asserts that every marked line is reported.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from ccf_runtime.cli.main import main
from ccf_runtime.http_api.app import HttpAuthority, create_app

if TYPE_CHECKING:
    from ccf_runtime.authz.protocol import TenantAuthorizerProtocol
    from ccf_runtime.http_api.auth import HttpAuthProtocol
    from ccf_runtime.http_api.dependencies import ApiDependencies


class _TwoSeams(TypedDict):
    auth: HttpAuthProtocol
    authorizer: TenantAuthorizerProtocol


def two_of_five(
    deps: ApiDependencies, auth: HttpAuthProtocol, authorizer: TenantAuthorizerProtocol
) -> None:
    bundle: HttpAuthority = {"auth": auth, "authorizer": authorizer}  # MISSING-SEAM-1
    main(["agent", "list"], dependencies=deps, authority=bundle)


def an_untyped_bag(deps: ApiDependencies, bag: dict[str, object]) -> None:
    main(["agent", "list"], dependencies=deps, authority=bag)  # MISSING-SEAM-2


def a_partial_splat(deps: ApiDependencies, partial: _TwoSeams) -> None:
    create_app(deps, **partial)  # MISSING-SEAM-3
