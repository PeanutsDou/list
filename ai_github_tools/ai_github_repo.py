import os

from .github_client import (
    resolve_github_token,
    github_request,
    get_authenticated_user,
    read_local_file_base64,
    build_json_payload,
    parse_repo_url
)
from .ai_github_git import (
    git_init_repo,
    git_add_all,
    git_commit,
    git_set_branch,
    git_add_or_set_remote,
    git_push
)

def _normalize_repo_path(value):
    if value is None:
        return ""
    raw = str(value).strip().strip("\"")
    if not raw:
        return ""
    normalized = raw.replace("\\", "/")
    if os.path.isabs(raw):
        if os.path.exists(raw):
            normalized = os.path.basename(raw)
        elif ":" in raw:
            normalized = os.path.basename(raw)
    normalized = normalized.lstrip("/").lstrip("./")
    return normalized


def _normalize_owner_repo(owner, repo, repo_url=""):
    owner_value = str(owner).strip() if owner else ""
    repo_value = str(repo).strip() if repo else ""
    if repo_value and "/" in repo_value and not owner_value:
        parts = repo_value.split("/", 1)
        owner_value = parts[0].strip()
        repo_value = parts[1].strip()
    if repo_url and (not owner_value or not repo_value):
        url_owner, url_repo = parse_repo_url(repo_url)
        if not owner_value:
            owner_value = url_owner
        if not repo_value:
            repo_value = url_repo
    return owner_value, repo_value


def _resolve_owner(owner, token, base_url=""):
    if owner:
        return {"status": "success", "owner": owner}
    user_info = get_authenticated_user(token, base_url=base_url)
    if user_info.get("status") != "success":
        return {"status": "error", "message": "无法获取登录用户信息", "data": user_info}
    login = None
    if isinstance(user_info.get("data"), dict):
        login = user_info["data"].get("login")
    if not login:
        return {"status": "error", "message": "无法获取登录用户信息"}
    return {"status": "success", "owner": login}


def _resolve_default_branch(owner, repo, token, base_url=""):
    repo_info = get_github_repo(owner, repo, token=token, base_url=base_url)
    if repo_info.get("status") != "success":
        return {"status": "error", "message": "无法获取仓库默认分支", "data": repo_info}
    if isinstance(repo_info.get("data"), dict):
        branch = repo_info["data"].get("default_branch")
        if branch:
            return {"status": "success", "branch": branch}
    return {"status": "error", "message": "无法获取仓库默认分支"}


def list_github_repos(token="", token_file="", visibility="all", affiliation="owner,collaborator,organization_member", per_page=100, page=1, base_url=""):
    auth_token = resolve_github_token(token, token_file)
    params = {
        "visibility": visibility,
        "affiliation": affiliation,
        "per_page": per_page,
        "page": page
    }
    return github_request("GET", "/user/repos", auth_token, base_url=base_url, params=params)


def get_github_repo(owner, repo, token="", token_file="", base_url=""):
    auth_token = resolve_github_token(token, token_file)
    owner_value, repo_value = _normalize_owner_repo(owner, repo)
    if not owner_value or not repo_value:
        return {"status": "error", "message": "仓库信息不完整"}
    path = f"/repos/{owner_value}/{repo_value}"
    return github_request("GET", path, auth_token, base_url=base_url)


def create_github_repo(name, description="", private=False, auto_init=True, default_branch="", token="", token_file="", base_url="", owner=""):
    auth_token = resolve_github_token(token, token_file)
    if not auth_token:
        return {"status": "error", "message": "缺少 GitHub Token"}
    payload = {
        "name": name,
        "description": description,
        "private": private,
        "auto_init": auto_init
    }
    if default_branch:
        payload["default_branch"] = default_branch
    target_owner = str(owner).strip() if owner else ""
    api_path = "/user/repos" if not target_owner else f"/orgs/{target_owner}/repos"
    return github_request("POST", api_path, auth_token, base_url=base_url, payload=build_json_payload(payload))


def delete_github_repo(owner, repo, token="", token_file="", base_url=""):
    auth_token = resolve_github_token(token, token_file)
    owner_value, repo_value = _normalize_owner_repo(owner, repo)
    if not owner_value or not repo_value:
        return {"status": "error", "message": "仓库信息不完整"}
    path = f"/repos/{owner_value}/{repo_value}"
    return github_request("DELETE", path, auth_token, base_url=base_url)


def update_github_repo(owner, repo, name=None, description=None, private=None, default_branch=None, homepage=None, has_issues=None, has_projects=None, has_wiki=None, token="", token_file="", base_url=""):
    auth_token = resolve_github_token(token, token_file)
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if private is not None:
        payload["private"] = private
    if default_branch is not None:
        payload["default_branch"] = default_branch
    if homepage is not None:
        payload["homepage"] = homepage
    if has_issues is not None:
        payload["has_issues"] = has_issues
    if has_projects is not None:
        payload["has_projects"] = has_projects
    if has_wiki is not None:
        payload["has_wiki"] = has_wiki
    if not payload:
        return {"status": "error", "message": "没有提供更新字段"}
    owner_value, repo_value = _normalize_owner_repo(owner, repo)
    if not owner_value or not repo_value:
        return {"status": "error", "message": "仓库信息不完整"}
    path = f"/repos/{owner_value}/{repo_value}"
    return github_request("PATCH", path, auth_token, base_url=base_url, payload=build_json_payload(payload))


def list_github_branches(owner, repo, per_page=100, page=1, token="", token_file="", base_url=""):
    auth_token = resolve_github_token(token, token_file)
    owner_value, repo_value = _normalize_owner_repo(owner, repo)
    if not owner_value or not repo_value:
        return {"status": "error", "message": "仓库信息不完整"}
    path = f"/repos/{owner_value}/{repo_value}/branches"
    params = {"per_page": per_page, "page": page}
    return github_request("GET", path, auth_token, base_url=base_url, params=params)


def create_github_branch(owner, repo, new_branch, base_branch="main", token="", token_file="", base_url=""):
    auth_token = resolve_github_token(token, token_file)
    owner_value, repo_value = _normalize_owner_repo(owner, repo)
    if not owner_value or not repo_value:
        return {"status": "error", "message": "仓库信息不完整"}
    base_ref = github_request("GET", f"/repos/{owner_value}/{repo_value}/git/ref/heads/{base_branch}", auth_token, base_url=base_url)
    if base_ref.get("status") != "success":
        return base_ref
    sha = None
    data = base_ref.get("data")
    if isinstance(data, dict):
        obj = data.get("object") or {}
        sha = obj.get("sha")
    if not sha:
        return {"status": "error", "message": "无法获取基准分支 SHA"}
    payload = {"ref": f"refs/heads/{new_branch}", "sha": sha}
    return github_request("POST", f"/repos/{owner_value}/{repo_value}/git/refs", auth_token, base_url=base_url, payload=payload)


def delete_github_branch(owner, repo, branch, token="", token_file="", base_url=""):
    auth_token = resolve_github_token(token, token_file)
    owner_value, repo_value = _normalize_owner_repo(owner, repo)
    if not owner_value or not repo_value:
        return {"status": "error", "message": "仓库信息不完整"}
    path = f"/repos/{owner_value}/{repo_value}/git/refs/heads/{branch}"
    return github_request("DELETE", path, auth_token, base_url=base_url)


def list_github_contents(owner, repo, path="", ref="", token="", token_file="", base_url=""):
    auth_token = resolve_github_token(token, token_file)
    owner_value, repo_value = _normalize_owner_repo(owner, repo)
    if not owner_value or not repo_value:
        return {"status": "error", "message": "仓库信息不完整"}
    normalized_path = _normalize_repo_path(path)
    api_path = f"/repos/{owner_value}/{repo_value}/contents/{normalized_path}" if normalized_path else f"/repos/{owner_value}/{repo_value}/contents"
    params = {}
    if ref:
        params["ref"] = ref
    return github_request("GET", api_path, auth_token, base_url=base_url, params=params)


def upload_github_file(owner, repo, local_path, target_path, branch="main", commit_message="update file", token="", token_file="", base_url=""):
    auth_token = resolve_github_token(token, token_file)
    owner_value, repo_value = _normalize_owner_repo(owner, repo)
    if not owner_value or not repo_value:
        return {"status": "error", "message": "仓库信息不完整"}
    if not local_path or not os.path.isfile(local_path):
        return {"status": "error", "message": "本地文件不存在"}
    if not target_path:
        target_path = os.path.basename(local_path)
    normalized_target = _normalize_repo_path(target_path)
    if not normalized_target:
        return {"status": "error", "message": "目标路径不能为空"}
    branch_value = str(branch).strip() if branch else ""
    if not branch_value:
        branch_info = _resolve_default_branch(owner_value, repo_value, auth_token, base_url=base_url)
        if branch_info.get("status") == "success":
            branch_value = branch_info.get("branch", "")
    file_data = read_local_file_base64(local_path)
    if file_data.get("status") != "success":
        return file_data
    api_path = f"/repos/{owner_value}/{repo_value}/contents/{normalized_target}"
    params = {"ref": branch_value} if branch_value else None
    existing = github_request("GET", api_path, auth_token, base_url=base_url, params=params)
    sha = None
    if existing.get("status") == "success" and isinstance(existing.get("data"), dict):
        sha = existing["data"].get("sha")
    payload = {
        "message": commit_message,
        "content": file_data["data"]
    }
    if branch_value:
        payload["branch"] = branch_value
    if sha:
        payload["sha"] = sha
    return github_request("PUT", api_path, auth_token, base_url=base_url, payload=payload)


def delete_github_file(owner, repo, target_path, branch="main", commit_message="delete file", token="", token_file="", base_url=""):
    auth_token = resolve_github_token(token, token_file)
    owner_value, repo_value = _normalize_owner_repo(owner, repo)
    if not owner_value or not repo_value:
        return {"status": "error", "message": "仓库信息不完整"}
    normalized_target = _normalize_repo_path(target_path)
    if not normalized_target:
        return {"status": "error", "message": "目标路径不能为空"}
    branch_value = str(branch).strip() if branch else ""
    if not branch_value:
        branch_info = _resolve_default_branch(owner_value, repo_value, auth_token, base_url=base_url)
        if branch_info.get("status") == "success":
            branch_value = branch_info.get("branch", "")
    api_path = f"/repos/{owner_value}/{repo_value}/contents/{normalized_target}"
    params = {"ref": branch_value} if branch_value else None
    existing = github_request("GET", api_path, auth_token, base_url=base_url, params=params)
    if existing.get("status") != "success":
        return existing
    sha = None
    if isinstance(existing.get("data"), dict):
        sha = existing["data"].get("sha")
    if not sha:
        return {"status": "error", "message": "无法获取文件 SHA"}
    payload = {"message": commit_message, "sha": sha}
    if branch_value:
        payload["branch"] = branch_value
    return github_request("DELETE", api_path, auth_token, base_url=base_url, payload=payload)


def create_repo_from_local_path(local_path, repo_name, description="", private=False, branch="", token="", token_file="", base_url="", owner="", repo_url="", commit_message="init", use_existing_repo=True, remote_name="origin"):
    if not local_path or not os.path.isdir(local_path):
        return {"status": "error", "message": "本地路径不存在"}
    auth_token = resolve_github_token(token, token_file)
    if not auth_token:
        return {"status": "error", "message": "缺少 GitHub Token"}
    owner_value, repo_value = _normalize_owner_repo(owner, repo_name, repo_url=repo_url)
    if not repo_value:
        return {"status": "error", "message": "仓库名称不能为空"}
    if not owner_value:
        owner_result = _resolve_owner("", auth_token, base_url=base_url)
        if owner_result.get("status") != "success":
            return owner_result
        owner_value = owner_result.get("owner", "")
    repo_info = get_github_repo(owner_value, repo_value, token=auth_token, base_url=base_url)
    repo_exists = repo_info.get("status") == "success"
    if repo_exists and not use_existing_repo:
        return {"status": "error", "message": "仓库已存在"}
    if not repo_exists:
        status_code = repo_info.get("status_code")
        if status_code and status_code != 404:
            return repo_info
        created = create_github_repo(
            name=repo_value,
            description=description,
            private=private,
            auto_init=False,
            token=auth_token,
            base_url=base_url,
            owner=owner_value
        )
        if created.get("status") != "success":
            return created
    init_result = git_init_repo(local_path)
    if init_result.get("status") != "success":
        return init_result
    add_result = git_add_all(local_path, exclude=["github token"])
    if add_result.get("status") != "success":
        return add_result
    commit_message_value = str(commit_message).strip() if commit_message else "init"
    commit_result = git_commit(local_path, commit_message_value)
    if commit_result.get("status") != "success" and commit_result.get("status_code") != 1:
        return commit_result
    branch_value = str(branch).strip() if branch else ""
    if not branch_value:
        if repo_exists and isinstance(repo_info.get("data"), dict):
            branch_value = repo_info["data"].get("default_branch", "")
        if not branch_value:
            branch_value = "main"
    branch_result = git_set_branch(local_path, branch_value)
    if branch_result.get("status") != "success":
        return branch_result
    remote_url = repo_url or f"https://github.com/{owner_value}/{repo_value}.git"
    remote_result = git_add_or_set_remote(local_path, remote_name, remote_url)
    if remote_result.get("status") != "success":
        return remote_result
    push_result = git_push(local_path, remote_name, branch_value, auth_token)
    if push_result.get("status") != "success":
        return push_result
    return {
        "status": "success",
        "message": "仓库已创建并推送",
        "data": {"owner": owner_value, "repo": repo_value, "remote": remote_url}
    }
