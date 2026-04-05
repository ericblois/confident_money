# CLA Setup

This file documents the GitHub-side steps needed to enforce Contributor License Agreement signing for pull requests.

## 1. Review the CLA Text

Confirm that `CLA.md` reflects the rights you want contributors to grant. If you want legal review, do that before enabling automated signing.

## 2. Create a GitHub Gist

Create a public GitHub Gist that contains the current contents of `CLA.md`. CLA Assistant uses the Gist text as the agreement contributors sign.

## 3. Install CLA Assistant

Install the CLA Assistant GitHub App for this repository:

- <https://github.com/apps/cla-assistant>

## 4. Connect the Repository

Open CLA Assistant and connect this repository to the Gist you created:

- <https://cla-assistant.io/>

Verify that the correct Gist is linked to the repository before moving on.

## 5. Configure Exceptions

If desired, allow specific bot accounts such as `dependabot[bot]` to bypass the CLA requirement.

## 6. Require the CLA Check Before Merge

In the repository's GitHub settings, create or update a branch ruleset for the default branch:

1. Require pull requests before merge.
2. Require status checks to pass before merge.
3. Select the CLA Assistant status check once it appears for the repository.

GitHub ruleset documentation:

- <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository>

## 7. Test the Workflow

Open a pull request from a different GitHub account and confirm that:

- CLA Assistant comments on the pull request;
- the pull request is blocked until the CLA is signed; and
- the status check passes after signing.

## 8. Maintain the CLA

When `CLA.md` changes:

- update the GitHub Gist to match the new text; and
- verify whether CLA Assistant requires contributors to re-sign the updated version.

## 9. Keep Records

Periodically export or back up the list of signed CLAs from CLA Assistant for your records.
