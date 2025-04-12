# Codecheck

An AI-powered code review GitHub Action that automatically reviews your pull requests using OpenAI's GPT models.

## Features

- Automatically reviews code on pull requests
- Uses OpenAI's GPT models for intelligent code review
- Configurable file exclusions
- Line-by-line code review comments
- Supports multiple programming languages

## Usage

1. Create a `.github/workflows/codecheck.yml` file in your repository with the following content:

```yaml
name: Codecheck

on:
  pull_request:
    types:
      - opened
      - synchronize
   push: 
    branches:
      - '**' # If you want to include every push

permissions: write-all
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Codecheck
        uses: anishavelayudhan/codecheck@main
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          openai_model: "gpt-4o" # Optional: defaults to 'gpt-4o'
          exclude: "**/*.json, **/*.md" # Optional excluding files
```

2. Add your OpenAI API key as a repository secret:
   - Go to your repository settings
   - Navigate to Secrets and Variables > Actions
   - Add a new secret named `OPENAI_API_KEY` with your OpenAI API key

## Configuration

The action supports the following configuration options:

- `openai_api_key`: Your OpenAI API key (required)
- `openai_model`: The OpenAI model to use (default: "gpt-4")
- `exclude`: Comma-separated list of file patterns to exclude from review (default: "**/\*.json, **/\*.md")

## Requirements

- GitHub Actions enabled for your repository
- OpenAI API key

## License

MIT
