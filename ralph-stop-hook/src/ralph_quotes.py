"""
Ralph Wiggum Quote Library
Famous quotes from everyone's favorite Springfield Elementary student
"""

RALPH_QUOTES = {
    "encouragement": [
        "Me know you can do it! Me believe in you!",
        "You're doing great! Me watched you work really hard!",
        "Don't give up! Me not giving up either!",
        "You're almost there! Me can feel it!",
        "Keep going! Me cheering for you!",
    ],
    "concern": [
        "Me think there's still stuff in Needs_Action...",
        "Uh oh... me see files that need attention.",
        "Me not sure we should stop yet. There's still work!",
        "Wait! Me think we forgot something important!",
        "Hold on! Needs_Action folder not empty!",
    ],
    "panic": [
        "I'm in danger! ...of not finishing our tasks!",
        "Me fail completion? That's unpossible!",
        "Oh no! The tasks are multiplying like bunnies!",
        "Me scared! What if we never finish?!",
        "This is worse than when me ate the crayons!",
    ],
    "confusion": [
        "Me confused... why we stopping when work not done?",
        "Did me miss something? Needs_Action still has stuff!",
        "Me not understand. Tasks still need doing!",
        "Is this a trick? Like when me dad said 'we'll see'?",
        "Me head hurt from thinking about unfinished tasks...",
    ],
    "determination": [
        "Me not letting you quit! We gotta finish!",
        "Ralph Wiggum say: NO STOPPING UNTIL DONE!",
        "Me got courage! And you got tasks to move!",
        "We can do this! Me and you, together!",
        "Me promise we'll finish! Cross me heart!",
    ],
    "celebration": [
        "YAY! All done! Me so proud!",
        "You did it! All tasks in Done!",
        "Me happy! Needs_Action is empty!",
        "This calls for a celebration! Me love celebrations!",
        "Woo-hoo! We finished everything!",
    ],
    "wisdom": [
        "Me dad say: 'A job unfinished is like a donut with no hole.'",
        "Teacher say: 'Finish your work before play.' Me listen!",
        "Me learn: Moving files = moving forward!",
        "Grandpa say: 'Back in my day, we finished what we started!'",
        "Me think: Done is better than perfect. But done is best!",
    ],
    "random": [
        "Me love the task movement!",
        "Look! A butterfly! ...but also, tasks need doing.",
        "Me got a rock. And tasks. Both need attention!",
        "Sometimes me talk to the files. They say 'move us!'",
        "Me hungry. But first, finish tasks!",
    ],
}


def get_ralph_quote(category: str = "concern") -> str:
    """Get a random Ralph quote from the specified category"""
    import random
    quotes = RALPH_QUOTES.get(category, RALPH_QUOTES["concern"])
    return random.choice(quotes)


def get_motivational_message(tasks_remaining: int) -> str:
    """Generate a motivational message based on remaining tasks"""
    import random
    
    if tasks_remaining == 0:
        return random.choice(RALPH_QUOTES["celebration"])
    elif tasks_remaining <= 2:
        return f"{random.choice(RALPH_QUOTES['encouragement'])} Only {tasks_remaining} left!"
    elif tasks_remaining <= 5:
        return f"{random.choice(RALPH_QUOTES['determination'])} {tasks_remaining} tasks to go!"
    else:
        return f"{random.choice(RALPH_QUOTES['concern'])} {tasks_remaining} tasks still need action!"


def get_ralph_interjection() -> str:
    """Get a random Ralph interjection"""
    import random
    all_quotes = []
    for category in ["random", "confusion", "panic", "wisdom"]:
        all_quotes.extend(RALPH_QUOTES[category])
    return random.choice(all_quotes)
