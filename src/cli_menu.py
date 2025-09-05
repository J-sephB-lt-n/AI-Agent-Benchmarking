"""CLI user interface to the application."""

from enum import Enum

import questionary


class MainAction(Enum):
    """First menu choices available to the user when running this script."""

    CREATE_EXPERIMENT = "Create new experiment"
    RUN_EXPERIMENT = "Run existing experiment"
    BROWSE_EXPERIMENT_RESULTS = "Browse experiment results"


main_action_user_choice: str = questionary.select(
    "What would you like to do?",
    choices=[x.value for x in MAIN_ACTION],
).ask()
main_action: MainAction = next(
    x for x in MainAction if x.value == main_action_user_choice
)

print(main_action)
