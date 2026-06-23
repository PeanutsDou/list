import os
import shutil
import subprocess


def _git_available():
    return shutil.which("git") is not None


def _run_git(args, cwd=None, token=None):
    if not _git_available():
        return {"status": "error", "message": "未检测到 git"}
    if not isinstance(args, list):
        return {"status": "error", "message": "参数格式错误"}
    cmd = ["git"] + args
    env = os.environ.copy()
    if token:
        cmd = ["git", "-c", f"http.extraheader=AUTHORIZATION: bearer {token}"] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "status_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def git_init_repo(local_path):
    if not local_path or not os.path.isdir(local_path):
        return {"status": "error", "message": "路径不存在"}
    if os.path.isdir(os.path.join(local_path, ".git")):
        return {"status": "success", "message": "已是 git 仓库"}
    return _run_git(["init"], cwd=local_path)


def git_add_all(local_path, exclude=None):
    if not local_path or not os.path.isdir(local_path):
        return {"status": "error", "message": "路径不存在"}
    args = ["add", "-A"]
    if exclude:
        args += ["--", "."]
        for item in exclude:
            value = str(item).strip()
            if value:
                args.append(f":(exclude){value}")
    return _run_git(args, cwd=local_path)


def git_commit(local_path, message):
    if not local_path or not os.path.isdir(local_path):
        return {"status": "error", "message": "路径不存在"}
    if not message:
        return {"status": "error", "message": "提交信息不能为空"}
    return _run_git(["commit", "-m", message], cwd=local_path)


def git_set_branch(local_path, branch):
    if not local_path or not os.path.isdir(local_path):
        return {"status": "error", "message": "路径不存在"}
    if not branch:
        return {"status": "error", "message": "分支名不能为空"}
    return _run_git(["branch", "-M", branch], cwd=local_path)


def git_add_or_set_remote(local_path, remote_name, remote_url):
    if not local_path or not os.path.isdir(local_path):
        return {"status": "error", "message": "路径不存在"}
    if not remote_name or not remote_url:
        return {"status": "error", "message": "远程配置不能为空"}
    existing = _run_git(["remote", "get-url", remote_name], cwd=local_path)
    if existing.get("status") == "success":
        return _run_git(["remote", "set-url", remote_name, remote_url], cwd=local_path)
    return _run_git(["remote", "add", remote_name, remote_url], cwd=local_path)


def git_push(local_path, remote="origin", branch="main", token=None):
    if not local_path or not os.path.isdir(local_path):
        return {"status": "error", "message": "路径不存在"}
    return _run_git(["push", "-u", remote, branch], cwd=local_path, token=token)


def git_clone_repo(repo_url, dest_path, branch="", token=None):
    if not repo_url:
        return {"status": "error", "message": "仓库地址不能为空"}
    args = ["clone", repo_url]
    if branch:
        args += ["-b", branch]
    if dest_path:
        args.append(dest_path)
    return _run_git(args, token=token)


def git_pull_repo(local_path, remote="origin", branch="", token=None):
    if not local_path or not os.path.isdir(local_path):
        return {"status": "error", "message": "路径不存在"}
    args = ["pull", remote]
    if branch:
        args.append(branch)
    return _run_git(args, cwd=local_path, token=token)


def git_checkout_branch(local_path, branch, create=False, start_point=""):
    if not local_path or not os.path.isdir(local_path):
        return {"status": "error", "message": "路径不存在"}
    if not branch:
        return {"status": "error", "message": "分支名不能为空"}
    if create:
        args = ["checkout", "-b", branch]
        if start_point:
            args.append(start_point)
        return _run_git(args, cwd=local_path)
    return _run_git(["checkout", branch], cwd=local_path)


def git_merge_branch(local_path, source_branch):
    if not local_path or not os.path.isdir(local_path):
        return {"status": "error", "message": "路径不存在"}
    if not source_branch:
        return {"status": "error", "message": "合并分支不能为空"}
    return _run_git(["merge", source_branch], cwd=local_path)


def git_push_repo(local_path, remote="origin", branch="main", token=None):
    return git_push(local_path, remote=remote, branch=branch, token=token)
