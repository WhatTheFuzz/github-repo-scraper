"""Iteratively get all public repositories from Github.

If an API token is provided, the script will authenticate with Github and
increase the rate limit from 60 to 5000 requests per hour. Otherwise, the
script will run without authentication and be limited to 60 requests per hour.

Example usage:
    python3 get-repos.py --token <API_TOKEN>
    python3 get-repos.py
"""

import sys
import argparse
import calendar
import time
import signal
import logging
from typing import Union
import numpy as np
import pandas as pd
from github import Github, GithubException, Repository
from github.GithubObject import NotSet
from github.GithubException import RateLimitExceededException
from github.PaginatedList import PaginatedList


def signal_handler(sig, frame):
    """Handles the SIGINT signal.
    I got tired of seeing the stack trace during debugging.
    """
    print("[+] Exiting...")
    sys.exit(0)


PROPERTIES = [
    "allow_auto_merge",
    "allow_forking",
    "allow_merge_commit",
    "allow_rebase_merge",
    "allow_squash_merge",
    "allow_update_branch",
    "archived",
    "archive_url",
    "blobs_url",
    "branches_url",
    "clone_url",
    "collaborators_url",
    "comments_url",
    "commits_url",
    "compare_url",
    "contents_url",
    "contributors_url",
    "created_at",
    "default_branch",
    "delete_branch_on_merge",
    "deployments_url",
    "description",
    "downloads_url",
    "events_url",
    "fork",
    "forks",
    "forks_count",
    "forks_url",
    "full_name",
    "git_commits_url",
    "git_refs_url",
    "git_tags_url",
    "git_url",
    "has_downloads",
    "has_issues",
    "has_pages",
    "has_projects",
    "has_wiki",
    "homepage",
    "hooks_url",
    "html_url",
    "id",
    "issue_comment_url",
    "issue_events_url",
    "issues_url",
    "keys_url",
    "labels_url",
    "language",
    "languages_url",
    "master_branch",
    "merges_url",
    "milestones_url",
    "mirror_url",
    "name",
    "network_count",
    "notifications_url",
    "open_issues",
    "open_issues_count",
    "organization",
    "owner",
    "parent",
    "permissions",
    "private",
    "pulls_url",
    "pushed_at",
    "releases_url",
    "size",
    "source",
    "ssh_url",
    "stargazers_count",
    "stargazers_url",
    "statuses_url",
    "subscribers_url",
    "subscribers_count",
    "subscription_url",
    "svn_url",
    "tags_url",
    "teams_url",
    "topics",
    "trees_url",
    "updated_at",
    "url",
    "visibility",
    "watchers",
    "watchers_count",
]


def get_max_id(df: pd.DataFrame) -> Union[int, NotSet]:
    """Returns the maximum id from the dataframe.
    The is is used as a reference to start pulling repositories. See the 
    `since` parameter in PyGithub.Github.get_repos method.
    If the id is NaN, returns NotSet.
    """
    try:
        max_index = df.id.max()
        if np.isnan(max_index):
            return NotSet
        return int(max_index)
    except ValueError as e:
        print(f"[-] Unknown index max: {df.id.max()}")
        raise e


def is_repo_we_care_about(repo: Repository) -> bool:
    """Filters the repositories we care about. Returns True if it passes the
    filter, False otherwise.
    """
    return repo.public and repo.language == "C" and not repo.fork


def save_repos_to_file(filename: str, repos: PaginatedList):
    """Appends the repositories to a file.
    Creates the file if it does not exist.
    """
    with open(filename, mode="a", encoding="utf-8") as f:
        try:
            for repo in repos:
                try:
                    print(f"[+] Found repo {repo.name}.")
                    # Create a dictionary entry for each repository.
                    repo_dict = {}
                    for prop in PROPERTIES:
                        if hasattr(repo, prop):
                            repo_dict[prop] = getattr(repo, prop)
                    #  Ensure that ID is an integer.
                    try:
                        int(repo_dict["id"])
                    except:
                        continue
                    df = pd.DataFrame(data=[repo_dict], columns=PROPERTIES)
                    df.to_csv(f, header=f.tell() == 0, index=False)
                except RateLimitExceededException as rate_limit_exceeded:
                    raise rate_limit_exceeded
                except GithubException as e:
                    if hasattr(e, "data"):
                        if hasattr(e.data, 'message'):
                            err_message = (
                                f"[+] {repo.name}: {e.data.get('message')} skipping."
                            )
                            # Log it to a file.
                            logging.error(err_message)
                            print(err_message)
                    else:
                        raise e
                    continue
        except RateLimitExceededException as rate_limit_exceeded:
            raise rate_limit_exceeded


def get_repos_with_backoff(github: Github, save_results_to: str, since: int = NotSet):
    """Gets all public repos from GitHub, starting from the given ID (since).
    Since the API is rate limited, this function will back off (sleep) until
    the rate limit has been reset.
    """
    print(f"[+] Getting repositories since: {since}")
    try:
        repos = github.get_repos(since=since, visibility="public")
        save_repos_to_file(filename=save_results_to, repos=repos)

    except RateLimitExceededException:
        core_rate_limit = github.get_rate_limit().core
        reset_timestamp = calendar.timegm(core_rate_limit.reset.timetuple())
        # Add 5 seconds to be sure the rate limit has been reset.
        sleep_time = reset_timestamp - calendar.timegm(time.gmtime()) + 5

        print(f"[+] Rate limit exceeded, backing off for {sleep_time} seconds.")
        # Sleep until the rate limit resets.
        time.sleep(sleep_time)

    # Open the CSV and get the last repository ID.
    df = pd.read_csv(
        save_results_to, usecols=["id"], dtype={"id": pd.Int64Dtype()}
    )
    last_id = get_max_id(df)
    get_repos_with_backoff(
        github=github, save_results_to=save_results_to, since=last_id
    )


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    logging.basicConfig(
        filename="errors.log",
        level=logging.ERROR,
        format="%(asctime)s %(message)s",
    )

    # argparse for the API token.
    parser = argparse.ArgumentParser(
        description="Get all public repositories from Github."
    )
    parser.add_argument("--token")
    parser.add_argument(
        "--filename",
        default="repos.csv",
        help="Filename to save the results to (as a CSV). "
        "Creates the file if it does not exist.",
    )
    args = parser.parse_args()
    api_token = args.token
    filename = args.filename

    if not api_token:
        print("[+] No API token provided, running script without authentication.")

    g = Github(login_or_token=api_token)

    try:
        print(
            f"[+] Successfully authenticated as {g.get_user().login}, "
            f"rate limit is: {g.get_rate_limit().core.remaining} out "
            f"of {g.get_rate_limit().core.limit}."
        )
    except GithubException:
        print(
            f"[+] Did not authenticate, but successfully connected to Github. "
            f"Rate limit is: {g.get_rate_limit().core.remaining} out "
            f"of {g.get_rate_limit().core.limit}."
        )
    # Check the CSV for the last seen index. The get_repo() uses the index as
    # the "since" parameter, so we can continue from where we left off.
    # Create the file if it does not exist.
    last_id = 0
    with open(filename, mode="a", encoding="utf-8") as f:
        if f.tell() != 0:
            df = pd.read_csv(filename, usecols=["id"], dtype={"id": pd.Int64Dtype()})
            last_id = get_max_id(df)

    get_repos_with_backoff(github=g, save_results_to="repos.csv", since=last_id)
