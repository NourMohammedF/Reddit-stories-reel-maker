import praw
import re
import os
import random
from collections import defaultdict

# Reddit API configuration
reddit = praw.Reddit(
    client_id='tbXaMJPIY0-7RXzXStwJ9w',
    client_secret='jJPuc5iDcvFKdEwaiplscFTSiNaoXw',
    user_agent='nour/1.0 by Emotional_Charge7965'
)

# Subreddit list
subreddits = [
    'LetsNotMeet', 'nosleep', 'EntitledPeople',
    'HistoricalWhatIf', 'TrueCrimeDiscussion', 'libraryofshadows',
    'UnresolvedMysteries', 'threekings', 'shortscarystories',
    'Thetruthishere', 'Paranormal', 'Glitch_in_the_Matrix',
    'ghoststories', 'horror', 'creepypasta', 'scarystories',
    'creepyencounters', 'Ghosts', 'TrueScaryStories'
]

# File paths
base_dir = os.path.dirname(os.path.abspath(__file__))
save_directory = os.path.join(base_dir, 'reddit stories')
used_posts_file = os.path.join(save_directory, "used_posts.txt")
story_subreddit_file = os.path.join(save_directory, "story_subreddit.txt")

# Create directory if missing
os.makedirs(save_directory, exist_ok=True)

# Enhanced Keyword Libraries
TITLE_KEYWORDS = {
    'horror': [
        'haunted', 'ghost', 'demon', 'possession', 'shadow figure',
        'entity', 'apparition', 'paranormal', 'occult', 'witchcraft',
        'cursed', 'ritual', 'satanic', 'necromancy', 'exorcism',
        'specter', 'wraith', 'poltergeist', 'banshee', 'hellscape',
        'eldritch', 'lovecraftian', 'abomination', 'sacrifice', 'ouija'
    ],
    'suspense': [
        'terrifying', 'chilling', 'blood-curdling', 'heart-stopping',
        'nerve-wracking', 'unsettling', 'disturbing', 'traumatic',
        'traumatizing', 'harrowing', 'petrifying', 'alarming',
        'dread-inducing', 'soul-chilling', 'gut-wrenching', 'spine-tingling',
        'nerve-shredding', 'mind-bending', 'reality-warping', 'sanity-testing'
    ],
    'mystery': [
        'unexplained', 'baffling', 'enigma', 'conundrum', 'puzzling',
        'cryptic', 'inexplicable', 'uncanny', 'sinister', 'ominous',
        'disquieting', 'foreboding', 'eerie', 'macabre', 'inscrutable',
        'perplexing', 'arcane', 'esoteric', 'obfuscated', 'labyrinthine'
    ],
    'action': [
        'confrontation', 'stalker', 'chase', 'escape', 'survival',
        'attack', 'ambush', 'break-in', 'kidnapping', 'hostage',
        'manhunt', 'showdown', 'revenge', 'retaliation', 'siege',
        'pursuit', 'skirmish', 'bloodbath', 'reckoning', 'ambush'
    ],
    'psychological': [
        'delusion', 'dissociation', 'paranoia', 'obsession', 'compulsion',
        'psychosis', 'fragmented', 'unraveling', 'fever-dream', 'gaslighting',
        'cognitive dissonance', 'existential', 'surreal', 'fractured'
    ]
}

STORY_KEYWORDS = {
    'sensory': [
        'guttural', 'piercing', 'deafening', 'acrid', 'putrid',
        'fetid', 'cloying', 'pungent', 'squelching', 'rasping',
        'screeching', 'thrumming', 'vibrating', 'trembling',
        'reeking', 'sulfurous', 'metallic', 'ear-splitting', 'ululating',
        'cacophonous', 'palpable', 'visceral', 'gut-churning', 'nauseating'
    ],
    'emotional': [
        'petrified', 'panic-stricken', 'terror-stricken', 'horror-struck',
        'paralyzed', 'hyperventilating', 'quivering', 'trembling',
        'shell-shocked', 'traumatized', 'disoriented', 'hysterical',
        'aghast', 'mortified', 'unhinged', 'dissociative', 'manic',
        'catatonic', 'existential dread', 'primordial fear'
    ],
    'physical': [
        'adrenaline', 'fight-or-flight', 'bloodshot', 'pale-faced',
        'goosebumps', 'cold sweat', 'tunnel vision', 'shallow breathing',
        'racing heart', 'clammy hands', 'dry mouth', 'lightheaded',
        'vertigo', 'nausea', 'tremors', 'muscle spasms', 'tachycardia',
        'vasoconstriction', 'auditory exclusion', 'time dilation'
    ],
    'environmental': [
        'claustrophobic', 'oppressive', 'sepulchral', 'funereal',
        'tenebrous', 'luminous', 'lurid', 'phantasmagoric', 'geometric',
        'non-euclidean', 'liminal', 'transitory', 'atemporal', 'suffocating',
        'labyrinthine', 'cyclopean', 'geometric', 'eldritch', 'abyssal'
    ],
    'supernatural': [
        'ectoplasm', 'apportation', 'teleportation', 'psychokinesis',
        'clairvoyance', 'precognition', 'retrocognition', 'telemetry',
        'bilocation', 'ectenic force', 'apparitional', 'transmogrification',
        'séance', 'channeling', 'mediumship', 'automatic writing',
        'electronic voice phenomena', 'orbs', 'vortex', 'shadow people'
    ]
}

def remove_links(text):
    return re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)

def replace_sensitive_content(text):
    replacement_rules = {
        r'\bdead body\b': 'd**d b*dy',
        r'\bmass shooting\b': 'm*ss sh**ting',
        r'\bsexual assault\b': 's*x**l a**ault',
        r'\bchild abuse\b': 'ch*ld ab*se',
        r'\bdrug overdose\b': 'dr*g ov*rd*se',
        r'\bgun violence\b': 'g*n v**lence',
        r'\bhuman remains\b': 'h*man r*m*ins',
        r'\bexplosive device\b': 'exp**sive d*v*ce',
        r'\bincest\b': 'in**st',
        r'\bscam(s)?\b': 'sc*m',
        r'\bfake news\b': 'f*ke n*ws',
        r'\bharass(s|ed)?\b': 'h*r*ss',
        r'\btheft\b': 'th*ft',
        r'\brob(s|bed)?\b': 'r*b',
        r'\bmug(s|ged)?\b': 'm*g',
        r'\bkill(s|ed|ing)?\b': 'k*lls',
        r'\bmurder(s|ed|er)?\b': 'm*rd*r',
        r'\bdead\b': 'd**d',
        r'\bdie(s|d)?\b': 'd**s',
        r'\bblood(y)?\b': 'bl**d',
        r'\bgun(s)?\b': 'g*n',
        r'\bweapon(s)?\b': 'w**pon',
        r'\battack(s|ed)?\b': 'att*ck',
        r'\bstab(s|bed)?\b': 'st*b',
        r'\bsex(s|ual)?\b': 's*x',
        r'\brape(s|d)?\b': 'r*pe',
        r'\bassault(s|ed)?\b': 'a**ault',
        r'\bporn\b': 'p*rn',
        r'\bpedo\b': 'p*d*',
        r'\bdrug(s)?\b': 'dr*gs',
        r'\bheroin\b': 'h**oin',
        r'\bcocaine\b': 'c**aine',
        r'\bmeth\b': 'm*th',
        r'\balcohol\b': 'a**ohol',
        r'\bsuicide(s)?\b': 's**cide',
        r'\bselfharm\b': 's*lfh*rm',
        r'\bracist(s|m)?\b': 'r*cist',
        r'\bnazi(s)?\b': 'n*zi',
        r'\bterror(ism|ist)?\b': 't*rror',
        r'\bcorpse(s)?\b': 'c*rpse',
        r'\bdecompose(s|d)?\b': 'd*comp*se',
        r'\brot(s)?\b': 'r*t',
        r'\bbomb(s)?\b': 'b*mb',
        r'\bkidnap(s)?\b': 'k*dnap',
        r'\bhuman trafficking\b': 'h* tr*ff*ck*ng',
        r'\btorture(s|d)?\b': 't*rt*re',
        r'\bvagina\b': 'v****a',
        r'\bpenis\b': 'p***s',
        r'\bbreast(s)?\b': 'b***st',
        

    }
    for pattern, replacement in replacement_rules.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def delete_existing_files():
    for file in ["title.txt", "story.txt"]:
        path = os.path.join(save_directory, file)
        if os.path.exists(path):
            os.remove(path)

def load_used_posts():
    if os.path.exists(used_posts_file):
        with open(used_posts_file, "r", encoding='utf-8') as f:
            return set(f.read().splitlines())
    return set()

def save_used_post(post_id):
    with open(used_posts_file, "a", encoding='utf-8') as f:
        f.write(post_id + "\n")

def remove_unwanted_symbols(text):
    symbols = [
        '͡', '¬', '©', '™', '®', '§', '†', '‡', '•', '°', '±', 'µ', '½', '¼', '⅓', '⅔', 
        '₣', '₧', '₨', '₩', '₹', '₲', '₺', '₼', '₽', '₿', '‽', '⁂', '⁑', '✂', '✏', '✑',
        '✒', '✓', '✔', '✘', '✗', '✚', '✛', '✜', '✝', '✞', '✟', '✠', '✡', '✵', '✶', 
        '✷', '✸', '✹', '✺', '✻', '✼', '✽', '✾', '✿', '❀', '❁', '❂', '❃', '❄', '❅', 
        '❆', '❇', '❈', '❉', '❊', '❋', '❍', '❎', '❏', '❐', '❑', '❒', '❓', '❔', '❕',
        '❖', '❗', '❘', '❙', '❚', '❛', '❜', '❝', '❞', '❟', '❠', '❡', '❢', '❣', '❤',
        '♡', '☞', '☜', '☹', '☺', '☻', '☼', '☽', '☾', '☿', '♀', '♂', '⚀', '⚁', '⚂',
        '⚃', '⚄', '⚅', '⚆', '⚇', '⚈', '⚉', '⚊', '⚋', '⚐', '⚑', '⚒', '⚓', '⚔',
        '⚕', '⚖', '⚗', '⚘', '⚙', '⚚', '⚛', '⚜', '⚝', '⚞', '⚟', '⚠', '⚡', '⚢',
        '⚣', '⚤', '⚥', '⚦', '⚧', '⚨', '⚩', '⚪', '⚫', '⚬', '⚭', '⚮', '⚯', '⚰',
        '⚱', '⚲', '⚳', '⚴', '⚵', '⚶', '⚷', '⚸', '⚹', '⚺', '⚻', '⚼', '⚽', '⚾',
        '⚿', '⛄', '⛅', '⛆', '⛇', '⛈', '⛉', '⛊', '⛋', '⛌', '⛍', '⛎', '⛏',
        '⛐', '⛑', '⛒', '⛓', '⛔', '⛕', '⛖', '⛗', '⛘', '⛙', '⛚', '⛛', '⛜',
        '⛝', '⛞', '⛟', '⛠', '⛡', '⛢', '⛣', '⛤', '⛥', '⛦', '⛧', '⛨', '⛩',
        '⛪', '⛫', '⛬', '⛭', '⛮', '⛯', '⛰', '⛱', '⛲', '⛳', '⛴', '⛵', '⛶',
        '⛷', '⛸', '⛹', '⛺', '⛻', '⛼', '⛽', '⛾', '⛿', '*', '/', '[', ']', 
        '{', '}', '_', '-', '+', '!', '@', '#', '$', '%', '^', '&', '<', '>', 
        '÷', '×', '|', '~', '`', '\\'
    ]

    return ''.join(c for c in text if c not in symbols)

def rate_title(title):
    score = 0
    title_lower = title.lower()
    
    # Question analysis
    if any(q in title_lower for q in ['who', 'what', 'where', 'why', 'how']):
        score += 2 if '?' in title else 1
    
    # Keyword scoring
    for category, keywords in TITLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                score += 2 if category in ['horror', 'action'] else 1
    
    # Structure analysis
    score += min(2, title.count('!') + title.count('?'))
    if 70 <= len(title) <= 200:
        score += 2
    
    # Pattern recognition
    if re.search(r'\b(I|We) (saw|heard|found|experienced)\b', title):
        score += 2
    if re.search(r'\b(Part \d+|Update)\b', title, re.IGNORECASE):
        score -= 3
    
    return max(0, score)

def rate_story(story, upvote_ratio):
    score = 0
    story_lower = story.lower()
    
    # Upvote scoring
    if upvote_ratio:
        score += min(4, int(upvote_ratio * 5))
    
    # Keyword density
    keyword_counts = defaultdict(int)
    for category, keywords in STORY_KEYWORDS.items():
        for keyword in keywords:
            keyword_counts[category] += story_lower.count(keyword)
    
    for count in keyword_counts.values():
        score += min(3, count)
    
    # Narrative structure
    paras = [p.strip() for p in story.split('\n') if p.strip()]
    score += min(3, len(paras) // 4)
    
    # Dialogue analysis
    if len(re.findall(r'["“”]', story)) / len(story.split()) > 0.03:
        score += 2
    
    # Suspense markers
    suspense_phrases = r'suddenly|without warning|out of nowhere|to my (horror|dismay)'
    score += len(re.findall(suspense_phrases, story_lower))
    
    # Temporal markers
    time_refs = len(re.findall(r'\b(minutes?|hours?|days?) (later|passed|went by)\b', story_lower))
    score += min(2, time_refs)
    
    return max(0, score)

def get_stories():
    used_posts = load_used_posts()
    quality_threshold = 12
    max_attempts = 100
    attempts = 0

    while attempts < max_attempts:
        attempts += 1
        subreddit = random.choice(subreddits)
        
        try:
            submissions = reddit.subreddit(subreddit).top(time_filter='month', limit=100)
            sorted_subs = sorted(
                submissions,
                key=lambda x: (x.score * (x.upvote_ratio or 0.7), x.num_comments),
                reverse=True
            )

            for submission in sorted_subs:
                if submission.id in used_posts or submission.over_18:
                    continue

                title = remove_unwanted_symbols(submission.title)
                story = remove_links(submission.selftext)
                story = remove_unwanted_symbols(story)
                
                if submission.selftext.lower().startswith("update"):
                    continue

                # Content filtering
                title = replace_sensitive_content(title)
                story = replace_sensitive_content(story)
                
                if not (800 <= len(story) <= 3500 and 50 <= len(title) <= 225):
                    continue

                # Quality scoring
                title_score = rate_title(title)
                story_score = rate_story(story, submission.upvote_ratio)
                engagement = min(5, submission.num_comments//50 + submission.score//500)
                total = title_score + story_score + engagement

                if total >= quality_threshold:
                    delete_existing_files()
                    
                    with open(os.path.join(save_directory, "title.txt"), "w", encoding='utf-8') as f:
                        f.write(title)
                    with open(os.path.join(save_directory, "story.txt"), "w", encoding='utf-8') as f:
                        f.write(story)
                    
                    save_used_post(submission.id)
                    with open(story_subreddit_file, "w", encoding='utf-8') as f:
                        f.write(subreddit)
                    return

        except Exception as e:
            print(f"Error processing {subreddit}: {str(e)}")
            continue

    print("No suitable stories found after 100 attempts")

# Run the script
if __name__ == "__main__":
    get_stories()