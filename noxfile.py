import nox

# The below setting make nox re-use any existing environment.
# If you find nox installing a lot of updates it makes sense to rebuild the environment.
# run: nox --no-reuse-existing-virtualenv
nox.options.reuse_existing_virtualenvs = True

PROJECT_FOLDER = "src"


@nox.session(python=False)
def fix_quality(session):
    """Fixes possible quality errors."""

    if session.posargs and session.posargs[0] == "skip-sync":
        skip_sync = True
    else:
        skip_sync = False

    if not skip_sync:
        session.run("poetry", "install", "--sync", external=True)

    session.run("black", PROJECT_FOLDER)
    session.run("black", "tests")

    session.run("ruff", PROJECT_FOLDER, "--fix")
    session.run("ruff", "tests", "--fix")


@nox.session
def quality(session):
    """This task also runs in the pipeline and should fail when something is wrong
    or needs changing. So some of the checks (like black and isort) are set to check-and-fail
    instead of automatically fixing it."""

    session.run("poetry", "install", "--sync", external=True)

    session.run("black", PROJECT_FOLDER, "--check")
    session.run("black", "tests", "--check")

    session.run("flake8", PROJECT_FOLDER)
    session.run("flake8", "tests")

    session.run("mypy", PROJECT_FOLDER)

    session.run("isort", PROJECT_FOLDER, "--check-only")
    session.run("isort", "tests", "--check-only")


@nox.session
def test(session):
    session.run("poetry", "install", "--sync", external=True)

    session.run("pytest", "tests")
