from . import main
import importlib

if __name__ == "__main__":
    # Import the lightweight CLI module to avoid executing heavy package-level imports
    cli = importlib.import_module('instyper.instyper_cli')
    cli.main() 