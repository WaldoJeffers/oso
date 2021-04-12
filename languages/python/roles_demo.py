# Demo

## Demo format

# one python file

# multiple levels of functionality
# 1. Built-in org roles (no customization)--basically equivalent to "global roles" in a multi-tenant app
#       - Owner, member, billing
#       - give some permissions
#       - show allow queries
# 2. Same-level implied roles
#       - show having "Owner" implies "Member" and "Billing"
# 3. Relationships + child permissions
#       - Add org-repo relationships
#       - Create repo permissions
#       - Add repo permissions to org
# 4. Add repo roles (different resources can have their own roles)
#       - Admin, Write, Read
#       - set these up as implied roles
#       - give some permissions
#       - show allow queries
#       - **we'll have to show how you take permissions off the org and switch over to implied roles**
# 5. Base repo permissions within an org (Implied roles across resource types based on relationships)
#       - Set up Org member base permissions for repos in org
#       - Org admin base permissions for repos in org
# 6. Customize the Org member role per organization
#       - Toggle for whether members can create private repos
#       - Create new permission
#       - Add scoped permission to member role for an org

## HAVEN'T IMPLEMENTED:

# 7. Customize base repo role for org members per organization
#       - Add scoped implication to the member role for an org
#       - scoped implication is only scoped to the parent (org) not the child (repo)
# 8. Customize base repo role for org members per repo
#       - Add scoped implication to the member role for a repo
#       - scoped implication is scoped to the child (repo)

from oso import Oso, OsoRoles
from dataclasses import dataclass


@dataclass
class User:
    name: str


@dataclass
class Organization:
    id: str


@dataclass
class Repository:
    id: str
    org: Organization


# 1. Built-in org roles (no customization)--basically equivalent to "global roles" in a multi-tenant app
#       - Owner, member, billing
#       - give some permissions
#       - show allow queries
def one():
    ###################### Configuration ######################################
    # Set up oso
    oso = Oso()
    oso.register_class(User)
    oso.register_class(Organization)

    # Set up roles
    roles = OsoRoles(oso)
    roles.register_class(User)
    roles.register_class(Organization)
    roles.register_class(Repository)
    roles.enable()

    # Simple policy that just uses roles
    policy = """
    role_resource(_resource: Organization, permissions, roles) if
        permissions = [
            "org_invite",
            "org_create_repo"
        ] and
        roles = {
            org_owner: {
                perms: ["org_invite"]
            },
            org_member: {
                perms: ["org_create_repo"]
            }
        };

    allow(actor, action, resource) if
        Roles.role_allows(actor, action, resource);
    """

    oso.load_str(policy)

    # Demo data
    osohq = Organization(id="osohq")

    leina = User(name="Leina")
    steve = User(name="Steve")

    # Things that happen in the app via the management api.
    roles.assign_role(leina, osohq, "org_owner")
    roles.assign_role(steve, osohq, "org_member")

    #### Test

    # Leina can invite people to osohq because she is an OWNER
    assert oso.is_allowed(leina, "invite", osohq)

    # Steve can create repos in osohq because he is a MEMBER
    assert oso.is_allowed(steve, "create_repo", osohq)

    # Steve can't invite people to osohq because only OWNERs can invite, and he's not an OWNER
    assert not oso.is_allowed(steve, "invite", osohq)

    # Oh no, Leina can't create a repo even though she's THE OWNER????
    assert not oso.is_allowed(leina, "create_repo", osohq)

    # We could give the owner role the create_repo permission, but what we really want to say is
    # that owners can do everything members can do. So the owner role implies the member role.


# 6. Customize the Org member role per organization
#       - Toggle for whether members can create private repos
#       - Create new permission
#       - Add scoped permission to member role for an org
def six():
    ###################### Configuration ######################################
    # Set up oso
    oso = Oso()
    oso.register_class(User)
    oso.register_class(Organization)
    oso.register_class(Repository)

    # Set up roles
    roles = OsoRoles(oso)

    # These will probably not be needed later but I need them for now.
    roles.register_class(User)
    roles.register_class(Organization)
    roles.register_class(Repository)

    roles.enable()

    # Policy
    policy = """
    role_resource(_resource: Organization, permissions, roles) if
        permissions = [
            "org_invite",
            "org_create_repo"
        ] and
        roles = {
            org_owner: {
                perms: ["org_invite"],
                implies: ["org_member", "repo_write"]
            },
            org_member: {
                perms: ["org_create_repo"],
                implies: ["repo_read"]
            }
        };

    role_resource(_resource: Repository, permissions, roles) if
        permissions = [
            "repo_push",
            "repo_pull"
        ] and
        roles = {
            repo_write: {
                perms: ["repo_push"],
                implies: ["repo_read"]
            },
            repo_read: {
                perms: ["repo_pull"]
            }
        };

    role_parent_resource(repository: Repository, parent_org: Organization) if
        repository.org = parent_org;

    allow(actor, action, resource) if
        Roles.role_allows(actor, action, resource);
    """
    oso.load_str(policy)

    # Demo data
    osohq = Organization(id="osohq")

    oso_repo = Repository(id="oso", org=osohq)

    leina = User(name="Leina")
    steve = User(name="Steve")
    gabe = User(name="Gabe")

    # Things that happen in the app via the management api.
    roles.assign_role(leina, osohq, "org_owner")
    roles.assign_role(steve, osohq, "org_member")

    roles.assign_role(gabe, oso_repo, "repo_write")

    #### Test

    ## Test Org roles

    # Leina can invite people to osohq because she is an OWNER
    assert oso.is_allowed(leina, "invite", osohq)

    # Steve can create repos in osohq because he is a MEMBER
    assert oso.is_allowed(steve, "create_repo", osohq)

    # Steve can't invite people to osohq because only OWNERs can invite, and he's not an OWNER
    assert not oso.is_allowed(steve, "invite", osohq)

    # Leina can create a repo because she's the OWNER and OWNER implies MEMBER
    assert oso.is_allowed(leina, "create_repo", osohq)

    # Steve can pull from oso_repo because he is a MEMBER of osohq
    # which implies READ on oso_repo
    assert oso.is_allowed(steve, "pull", oso_repo)
    # Leina can pull from oso_repo because she's an OWNER of osohq
    # which implies WRITE on oso_repo
    # which implies READ on oso_repo
    assert oso.is_allowed(leina, "pull", oso_repo)
    # Gabe can pull from oso_repo because he has WRTIE on oso_repo
    # which implies READ on oso_repo
    assert oso.is_allowed(gabe, "pull", oso_repo)

    # Steve can NOT push to oso_repo because he is a MEMBER of osohq
    # which implies READ on oso_repo but not WRITE
    assert not oso.is_allowed(steve, "push", oso_repo)
    # Leina can push to oso_repo because she's an OWNER of osohq
    # which implies WRITE on oso_repo
    assert oso.is_allowed(leina, "push", oso_repo)
    # Gabe can push to oso_repo because he has WRTIE on oso_repo
    assert oso.is_allowed(gabe, "push", oso_repo)


if __name__ == "__main__":
    one()
    six()
    print("it works")
