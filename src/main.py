import os
import base64
import glob
from github import Github
from openai import OpenAI
from dotenv import load_dotenv

# Supported OpenAI models
SUPPORTED_MODELS = [
    'gpt-4o',
    'gpt-4',
    'gpt-4-turbo-preview',
    'gpt-3.5-turbo',
    'gpt-3.5-turbo-16k',
]

def load_environment():
    """Load and validate required environment variables."""
    load_dotenv()

    github_token = os.getenv('GITHUB_TOKEN')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    github_repo = os.getenv('GITHUB_REPOSITORY')
    event_name = os.getenv('GITHUB_EVENT_NAME')
    model = os.getenv('OPENAI_API_MODEL', 'gpt-4o')
    exclude = os.getenv('EXCLUDE')

    if not github_token:
        raise EnvironmentError("GITHUB_TOKEN is required.")
    if not openai_api_key:
        raise EnvironmentError("OPENAI_API_KEY is required.")
    if not github_repo:
        raise EnvironmentError("GITHUB_REPOSITORY is required.")
    if not event_name:
        raise EnvironmentError("GITHUB_EVENT_NAME is required.")

    validate_model(model)

    return {
        'github_token': github_token,
        'openai_api_key': openai_api_key,
        'github_repo': github_repo,
        'event_name': event_name,
        'model': model,
        'exclude': exclude,
    }

def validate_model(model_name):
    """Ensure the OpenAI model is supported."""
    if model_name not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported model: {model_name}. Supported: {', '.join(SUPPORTED_MODELS)}")

def should_exclude_file(filename, files_exclude):
    """Determine if a file should be excluded."""
    if files_exclude is None:
        files_exclude = "" 
    files = [f.strip() for f in files_exclude.split(',')]
    return any(glob.fnmatch.fnmatch(filename, file) for file in files)

def get_file_content(repo, path, ref):
    """Fetch file content from GitHub at a specific ref."""
    try:
        content_file = repo.get_contents(path, ref=ref)
        return base64.b64decode(content_file.content).decode('utf-8')
    except Exception as e:
        print(f"[Error] Failed to get content for {path}: {e}")
        return None

def review_code(client, code, model):
    """Request a code review from OpenAI."""
    try:
        max_tokens = 4000 if model.startswith("gpt-4") else 2000

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a code reviewer. Focus only on the **changed or added parts** of the code in the provided diff."
                        " Only suggest improvements if there is something that can **improve functionality, performance, or maintainability**."
                        " If there are no improvements that can be made, leave **no comments**."
                        " Ignore minor changes that **do not affect functionality**, performance, or maintainability."
                        " Cosmetic changes or trivial changes that **do not impact overall behavior** should be ignored."
                        " Your feedback should be **actionable**, **concise**, and **focused only on the changes**."
                        " If the change does not have a clear **functional impact**, **do not comment**."
                        " **Avoid suggesting changes for the sake of style** or formatting unless it impacts functionality."
                        " Do not suggest adding comments to the code."
                        " Use the commit message or PR description for overall context, but focus only on the **code itself**."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Review this code:\n\n{code}",
                },
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Error] Failed to get AI review: {e}")
        return None

def process_pull_request(repo, pr, client, model, exclude):
    """Process and review files in a pull request."""
    print(f"Reviewing Pull Request #{pr.number}")

    for file in pr.get_files():
        if file.status == 'removed' or should_exclude_file(file.filename, exclude):
            continue

        content = get_file_content(repo, file.filename, pr.head.sha)
        if not content:
            continue

        review = review_code(client, content, model)
        if review:
            pr.create_review(body=review, event='COMMENT')
            print(f"[Review Added] {file.filename}")

def process_push_commit(repo, commit_sha, client, model, exclude):
    """Process and review files in a pushed commit."""
    commit = repo.get_commit(commit_sha)
    print(f"Reviewing Push Commit: {commit.sha}")
    
    full_review = []

    for file in commit.files:
        if file.status == 'removed' or should_exclude_file(file.filename, exclude):
            continue

        patch = file.patch
        if not patch:
            continue

        review = review_code(client, patch, model)
        if review:
            print(f"\n[Review for {file.filename}]\n{review}\n")
            full_review.append(f"### `{file.filename}`\n{review}")
    
    if full_review:
        comment_body = "## ✅ CodeCheck Summary\n" + "\n\n".join(full_review)
        try:
            commit.create_comment(body=comment_body)
            print(f"[✓] Posted review comment on commit {commit.sha}")
            for comment in commit.get_comments():
                print(comment.body)
        except Exception as e:
            print(f"[Error] Could not post comment: {e}")
    else:
        print("No files reviewed or no feedback generated.")

def main():
    config = load_environment()

    # Initialize clients
    github = Github(config['github_token'])
    openai_client = OpenAI(api_key=config['openai_api_key'])
    repo = github.get_repo(config['github_repo'])

    if config['event_name'] == 'pull_request':
        pr_number = int(os.getenv('GITHUB_REF').split('/')[-2])
        pr = repo.get_pull(pr_number)
        process_pull_request(repo, pr, openai_client, config['model'], config['exclude'])

    elif config['event_name'] == 'push':
        commit_sha = os.getenv('GITHUB_SHA')
        process_push_commit(repo, commit_sha, openai_client, config['model'], config['exclude'])

    else:
        print(f"[Warning] Unsupported GitHub event: {config['event_name']}")

if __name__ == "__main__":
    main()
