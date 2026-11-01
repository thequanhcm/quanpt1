"""
V27 M2 - Authorization: RBAC + simple ABAC (deny-by-default).

In-memory Role/Permission model with role hierarchy and a simple
attribute-based (ABAC) policy check. SIMULATED security skeleton:
no persistence, no distributed policy store, no policy versioning.

Design:
- Permission: "resource:action" strings (e.g. "document:read").
- Role: named set of permissions + optional parent roles (hierarchy).
- RBACEngine.check(): deny-by-default; a subject's effective permissions
  are the union of its roles' permissions, expanded through the hierarchy.
- ABACEngine.evaluate(): simple attribute-match policies. A policy grants
  access only when EVERY required attribute matches the subject/resource/
  environment attributes. No policy match => deny (deny-by-default).
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

__all__ = [
    "Permission",
    "Role",
    "RBACEngine",
    "ABACPolicy",
    "ABACEngine",
    "AccessDecision",
    "AuthorizationEngine",
]

WILDCARD = "*"


@dataclass(frozen=True)
class Permission:
    """Fine-grained permission: action allowed on a resource pattern."""

    resource: str
    action: str

    def matches(self, resource: str, action: str) -> bool:
        """Glob-style match on resource and action ("*" wildcard)."""
        return fnmatch.fnmatchcase(resource, self.resource) and fnmatch.fnmatchcase(action, self.action)

    def as_string(self) -> str:
        return f"{self.resource}:{self.action}"


@dataclass
class Role:
    """Role = permission set + optional parents (role hierarchy)."""

    name: str
    permissions: List[Permission] = field(default_factory=list)
    parent_names: List[str] = field(default_factory=list)
    description: str = ""

    def add_permission(self, permission: Permission) -> None:
        if permission not in self.permissions:
            self.permissions.append(permission)


@dataclass
class AccessDecision:
    """Result of an authorization check (explainable)."""

    allowed: bool
    reason: str
    matched_policy: Optional[str] = None
    via_role: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "matched_policy": self.matched_policy,
            "via_role": self.via_role,
        }


class RBACEngine:
    """Role-based access control with hierarchy and deny-by-default."""

    def __init__(self) -> None:
        self._roles: Dict[str, Role] = {}
        self._user_roles: Dict[str, set] = {}

    # -- role management ------------------------------------------------
    def add_role(self, role: Role) -> Role:
        self._roles[role.name] = role
        return role

    def get_role(self, name: str) -> Optional[Role]:
        return self._roles.get(name)

    def remove_role(self, name: str) -> bool:
        return self._roles.pop(name, None) is not None

    def assign_role_to_user(self, user_id: str, role_name: str) -> None:
        """Convenience: track user->role assignments inside the engine.

        (Production systems would keep assignments in the user store.)
        """
        self._user_roles.setdefault(user_id, set()).add(role_name)

    def revoke_role_from_user(self, user_id: str, role_name: str) -> None:
        roles = self._user_roles.get(user_id)
        if roles is not None:
            roles.discard(role_name)

    def roles_of(self, user_id: str) -> List[str]:
        return sorted(self._user_roles.get(user_id, set()))

    # -- hierarchy -------------------------------------------------------
    def effective_roles(self, role_name: str) -> List[str]:
        """All roles reachable through parent links (including self).

        Cycle-safe: tracks visited names.
        """
        visited: List[str] = []
        stack = [role_name]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.append(current)
            role = self._roles.get(current)
            if role is not None:
                stack.extend(role.parent_names)
        return visited

    def effective_permissions(self, user_id: str) -> List[Permission]:
        """Union of permissions across all roles of a user (hierarchy-expanded)."""
        perms: Dict[str, Permission] = {}
        for role_name in self.roles_of(user_id):
            for eff in self.effective_roles(role_name):
                role = self._roles.get(eff)
                if role is None:
                    continue
                for perm in role.permissions:
                    perms[f"{perm.resource}:{perm.action}"] = perm
        return list(perms.values())

    # -- checking --------------------------------------------------------
    def check(
        self,
        user_id: str,
        resource: str,
        action: str,
        role_names: Optional[Iterable[str]] = None,
    ) -> AccessDecision:
        """Deny-by-default RBAC check.

        `role_names` may be passed explicitly (caller-known roles);
        otherwise assignments registered via assign_role_to_user are used.
        """
        if role_names is not None:
            subject_roles = list(role_names)
        else:
            subject_roles = self.roles_of(user_id)
        for role_name in subject_roles:
            for eff in self.effective_roles(role_name):
                role = self._roles.get(eff)
                if role is None:
                    continue
                for perm in role.permissions:
                    if perm.matches(resource, action):
                        return AccessDecision(
                            allowed=True,
                            reason=f"permission {perm.as_string()} via role '{role_name}' -> '{eff}'",
                            via_role=eff,
                        )
        return AccessDecision(
            allowed=False,
            reason="deny-by-default: no role grants the requested permission",
        )


class ABACPolicy:
    """Simple attribute-match policy: every required attr must match.

    Requirements reference three attribute bags:
    - "subject"  (e.g. department, clearance)
    - "resource" (e.g. owner, classification)
    - "environment" (e.g. time_of_day, network_zone)

    A required value may be a single value or a list of acceptable values.
    """

    def __init__(
        self,
        name: str,
        required_attributes: Dict[str, Any],
        effect: str = "allow",
    ) -> None:
        if effect not in ("allow", "deny"):
            raise ValueError("effect must be 'allow' or 'deny'")
        self.name = name
        self.required_attributes = dict(required_attributes)
        self.effect = effect

    def matches(self, subject: Dict[str, Any], resource: Dict[str, Any], environment: Dict[str, Any]) -> bool:
        bags = {"subject": subject, "resource": resource, "environment": environment}
        for key, required in self.required_attributes.items():
            bag_name, _, attr_name = key.partition(".")
            bag = bags.get(bag_name)
            if bag is None:
                return False
            actual = bag.get(attr_name)
            acceptable = required if isinstance(required, list) else [required]
            if actual not in acceptable:
                return False
        return True


class ABACEngine:
    """Evaluates ABAC policies; first matching policy decides (deny otherwise)."""

    def __init__(self) -> None:
        self._policies: List[ABACPolicy] = []

    def add_policy(self, policy: ABACPolicy) -> ABACPolicy:
        self._policies.append(policy)
        return policy

    def list_policies(self) -> List[ABACPolicy]:
        return list(self._policies)

    def evaluate(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        environment: Dict[str, Any],
    ) -> AccessDecision:
        for policy in self._policies:
            if policy.matches(subject, resource, environment):
                if policy.effect == "allow":
                    return AccessDecision(
                        allowed=True,
                        reason=f"ABAC policy '{policy.name}' matched",
                        matched_policy=policy.name,
                    )
                return AccessDecision(
                    allowed=False,
                    reason=f"ABAC deny policy '{policy.name}' matched",
                    matched_policy=policy.name,
                )
        return AccessDecision(allowed=False, reason="deny-by-default: no ABAC policy matched")


class AuthorizationEngine:
    """Combined RBAC + ABAC decision point (deny-by-default overall).

    Order: explicit ABAC deny > RBAC > ABAC allow > default deny.
    """

    def __init__(self, rbac: Optional[RBACEngine] = None, abac: Optional[ABACEngine] = None) -> None:
        self.rbac = rbac or RBACEngine()
        self.abac = abac or ABACEngine()

    def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        role_names: Optional[Iterable[str]] = None,
        subject_attrs: Optional[Dict[str, Any]] = None,
        resource_attrs: Optional[Dict[str, Any]] = None,
        environment_attrs: Optional[Dict[str, Any]] = None,
    ) -> AccessDecision:
        subject_attrs = subject_attrs or {}
        resource_attrs = resource_attrs or {}
        environment_attrs = environment_attrs or {}

        # 1. An explicit ABAC deny policy wins immediately.
        for policy in self.abac.list_policies():
            if policy.effect == "deny" and policy.matches(subject_attrs, resource_attrs, environment_attrs):
                return AccessDecision(
                    allowed=False,
                    reason=f"ABAC deny policy '{policy.name}' matched",
                    matched_policy=policy.name,
                )

        # 2. RBAC grant.
        rbac_decision = self.rbac.check(user_id, resource, action, role_names=role_names)
        if rbac_decision.allowed:
            return rbac_decision

        # 3. ABAC allow policy.
        abac_decision = self.abac.evaluate(subject_attrs, resource_attrs, environment_attrs)
        if abac_decision.allowed:
            return abac_decision

        # 4. Deny-by-default.
        return AccessDecision(
            allowed=False,
            reason=f"deny-by-default (rbac: {rbac_decision.reason}; abac: {abac_decision.reason})",
        )
