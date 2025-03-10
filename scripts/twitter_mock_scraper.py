#!/usr/bin/env python3
"""
Twitter Mock Data Generator for GlovePost

This script generates mock Twitter/X data for testing without requiring
external API access or web scraping. Perfect for development and testing
without hitting rate limits or connection issues.
"""

import os
import json
import logging
import argparse
import datetime
import sys
import random
from typing import List, Dict, Any

# Setup logging
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "twitter_mock_scraper.log")),
        logging.StreamHandler(sys.stderr)  # Explicitly log to stderr
    ]
)
logger = logging.getLogger("TwitterMockScraper")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Generate mock Twitter/X content')
parser.add_argument('--accounts', type=str, default='AP,Reuters,BBCWorld,nytimes,guardian,techcrunch,TheEconomist,espn,NatGeo,WIRED',
                   help='Comma-separated list of Twitter account usernames')
parser.add_argument('--limit', type=int, default=5, help='Number of tweets to generate per account')
args = parser.parse_args()

# Parse accounts from comma-separated string to list
if isinstance(args.accounts, str):
    args.accounts = [account.strip() for account in args.accounts.split(',') if account.strip()]
    logger.info(f"Processing {len(args.accounts)} Twitter accounts from comma-separated list")

# News outlet templates
NEWS_TEMPLATES = [
    "BREAKING: {topic} as officials announce new measures.",
    "UPDATE: {topic} - experts weigh in on developments.",
    "JUST IN: {topic}, according to a new report.",
    "Sources confirm that {topic} amid growing concerns.",
    "Our correspondent reports that {topic} as situation unfolds.",
    "ANALYSIS: What {topic} means for the future.",
    "DEVELOPING STORY: {topic} with more updates to follow.",
    "EXCLUSIVE: {topic}, our investigation reveals.",
    "{topic} - here's what you need to know.",
    "FACTCHECK: {topic} - separating truth from fiction."
]

# Tech outlet templates
TECH_TEMPLATES = [
    "JUST ANNOUNCED: {tech_company} unveils {tech_product}.",
    "REVIEW: We tested {tech_product} and here's what we found.",
    "REPORT: {tech_company} is developing {tech_concept}, sources say.",
    "ANALYSIS: How {tech_concept} will change the industry.",
    "BREAKING: {tech_company} acquires {tech_company2} for ${amount} billion.",
    "EXCLUSIVE: Inside {tech_company}'s plan to revolutionize {tech_sector}.",
    "LEAKED: {tech_product} specs reveal {tech_feature}.",
    "The future of {tech_sector}: Why {tech_concept} matters.",
    "5 ways {tech_concept} will impact your daily life.",
    "{tech_company} CEO speaks out on {tech_policy_issue}."
]

# Sports outlet templates
SPORTS_TEMPLATES = [
    "BREAKING: {team} defeats {team2} {score} in dramatic {sport} match.",
    "TRANSFER NEWS: {player} joins {team} in ${amount}M deal.",
    "INJURY UPDATE: {player} expected to miss {time_period} with {injury}.",
    "POST-GAME: {coach} reacts to {team}'s {outcome} against {team2}.",
    "ANALYSIS: How {team}'s strategy led to {outcome} in {competition}.",
    "BREAKING RECORD: {player} becomes first to {achievement} in {sport} history.",
    "MATCH PREVIEW: {team} faces {team2} in crucial {competition} clash.",
    "RETIREMENT: {player} announces end to {adjective} {sport} career.",
    "SCANDAL: {team} under investigation for alleged {violation}.",
    "COMEBACK: {player} returns to {team} after {time_period} absence."
]

# Entertainment outlet templates
ENTERTAINMENT_TEMPLATES = [
    "BREAKING: {celebrity} to star in upcoming {genre} film '{movie_title}'.",
    "REVIEW: '{movie_title}' is the {adjective} {genre} film of the year.",
    "RED CARPET: {celebrity} stuns at {award_show} in {designer} gown.",
    "EXCLUSIVE: {celebrity} opens up about {personal_topic} in candid interview.",
    "JUST ANNOUNCED: '{tv_show}' renewed for {number} more seasons.",
    "CONCERT REVIEW: {musician}'s {city} show was {adjective}.",
    "LEAKED: First look at {celebrity} in '{movie_title}' revealed.",
    "CONTROVERSY: {celebrity} responds to backlash over {controversy_topic}.",
    "CASTING NEWS: {celebrity} to replace {celebrity2} in '{movie_title}'.",
    "BOX OFFICE: '{movie_title}' earns ${amount}M in opening weekend."
]

# Science outlet templates
SCIENCE_TEMPLATES = [
    "BREAKTHROUGH: Scientists discover {science_discovery} that could revolutionize {field}.",
    "STUDY: Research shows link between {factor} and {effect}, publication reveals.",
    "SPACE: {space_object} observed by {telescope} provides new insights into {space_phenomenon}.",
    "CLIMATE: New data indicates {climate_finding}, researchers warn.",
    "MEDICINE: Clinical trials for {treatment} show promising results for {disease} patients.",
    "TECHNOLOGY: New {tech_invention} could solve {problem}, scientists say.",
    "BIOLOGY: Researchers identify {organism} with unusual ability to {biological_function}.",
    "ARCHAEOLOGY: Ancient {artifact} discovered in {location} dates back {time_period}.",
    "PHYSICS: Experiment confirms {physics_theory} with implications for {field}.",
    "ENVIRONMENT: Study finds {environment_finding} at unprecedented rates."
]

# Content topics by category
TOPICS = {
    "News": [
        "global leaders meet for climate summit",
        "new economic sanctions imposed",
        "peace talks resume between warring nations",
        "landmark legislation passes with bipartisan support",
        "major infrastructure bill announced",
        "election results contested in key battleground",
        "humanitarian crisis worsens in conflict zone",
        "new trade agreement reached between nations",
        "protests erupt over controversial policy",
        "government announces sweeping reforms"
    ],
    "Tech": {
        "tech_company": ["Apple", "Google", "Microsoft", "Meta", "Amazon", "Tesla", "SpaceX", "Samsung", "Intel", "NVIDIA"],
        "tech_company2": ["Twitter", "Slack", "Zoom", "Spotify", "Netflix", "Discord", "Roblox", "Figma", "Notion", "Canva"],
        "tech_product": ["next-gen AI assistant", "foldable smartphone", "AR glasses", "neural interface", "quantum computer", "electric vehicle", "smart home system", "privacy-focused browser", "cloud gaming platform", "digital wallet"],
        "tech_concept": ["artificial general intelligence", "the metaverse", "blockchain technology", "quantum computing", "neural interfaces", "autonomous vehicles", "extended reality", "edge computing", "digital privacy", "synthetic media"],
        "tech_sector": ["healthcare", "finance", "education", "transportation", "entertainment", "retail", "manufacturing", "energy", "agriculture", "cybersecurity"],
        "tech_feature": ["unprecedented battery life", "revolutionary AI capabilities", "groundbreaking performance", "unmatched security features", "seamless cross-platform integration", "zero-latency response", "advanced privacy controls", "next-gen cooling system", "innovative user interface", "modular design"],
        "tech_policy_issue": ["data privacy", "content moderation", "right to repair", "algorithmic transparency", "digital taxation", "platform monopolies", "AI regulation", "net neutrality", "cybersecurity standards", "digital identity"],
        "amount": ["1", "2", "3", "5", "10", "15", "20", "25", "30", "50"]
    },
    "Sports": {
        "sport": ["football", "basketball", "soccer", "tennis", "baseball", "hockey", "golf", "rugby", "cricket", "boxing"],
        "team": ["Chiefs", "Lakers", "Manchester United", "Yankees", "Maple Leafs", "Barcelona", "Warriors", "Liverpool", "Dodgers", "Celtics"],
        "team2": ["Patriots", "Bucks", "Real Madrid", "Red Sox", "Flyers", "Bayern Munich", "Suns", "Chelsea", "Giants", "Heat"],
        "player": ["Tom Brady", "LeBron James", "Lionel Messi", "Serena Williams", "Mike Trout", "Sidney Crosby", "Tiger Woods", "Cristiano Ronaldo", "Aaron Judge", "Steph Curry"],
        "coach": ["Andy Reid", "Steve Kerr", "Pep Guardiola", "Erik Spoelstra", "Bill Belichick", "Jürgen Klopp", "Gregg Popovich", "Pat Riley", "Nick Saban", "John Calipari"],
        "competition": ["playoffs", "championship", "final", "tournament", "league", "division", "cup", "series", "masters", "open"],
        "outcome": ["victory", "defeat", "comeback", "upset", "blowout", "heartbreaking loss", "dominant performance", "nail-biting win", "historic triumph", "surprising draw"],
        "injury": ["knee injury", "hamstring strain", "concussion", "ankle sprain", "shoulder injury", "back issues", "groin pull", "broken hand", "torn ACL", "calf strain"],
        "achievement": ["score 100 points", "win 10 championships", "break the all-time record", "achieve a perfect season", "win MVP three times", "complete the triple crown", "earn Olympic gold", "sweep all majors", "go undefeated", "set a world record"],
        "violation": ["salary cap violations", "performance enhancing drugs", "match fixing", "improper recruiting", "tampering", "unsportsmanlike conduct", "illegal equipment", "breaking protocol", "code of conduct breach", "financial irregularities"],
        "time_period": ["3 weeks", "6 months", "entire season", "two years", "playoff run", "indefinite period", "three games", "summer break", "rehabilitation period", "contract dispute"],
        "score": ["28-24", "4-2", "110-105", "3-1", "2-0", "6-5", "1-0", "7-3", "21-17", "5-4"],
        "adjective": ["legendary", "disappointing", "record-breaking", "inspiring", "controversial", "dominant", "unexpected", "historic", "remarkable", "stellar"]
    },
    "Entertainment": {
        "celebrity": ["Tom Hanks", "Jennifer Lawrence", "Dwayne Johnson", "Zendaya", "Ryan Reynolds", "Emma Stone", "Denzel Washington", "Scarlett Johansson", "Leonardo DiCaprio", "Viola Davis"],
        "celebrity2": ["Chris Pratt", "Florence Pugh", "Idris Elba", "Ana de Armas", "Chris Hemsworth", "Margot Robbie", "Daniel Kaluuya", "Anya Taylor-Joy", "Timothée Chalamet", "Lupita Nyong'o"],
        "movie_title": ["The Last Horizon", "Midnight Echoes", "Eternal Shadows", "Quantum Dreams", "The Lost City", "Silver Linings", "Phoenix Rising", "Ocean's Legacy", "Parallel Lives", "The Final Countdown"],
        "tv_show": ["Stranger Things", "The Mandalorian", "Succession", "The Crown", "Ted Lasso", "Euphoria", "The Last of Us", "House of the Dragon", "Wednesday", "Yellowstone"],
        "musician": ["Taylor Swift", "BTS", "Beyoncé", "Harry Styles", "Bad Bunny", "Adele", "Drake", "Billie Eilish", "The Weeknd", "Olivia Rodrigo"],
        "award_show": ["Oscars", "Grammys", "Emmys", "Met Gala", "Golden Globes", "SAG Awards", "VMAs", "Tony Awards", "Cannes Film Festival", "BAFTA Awards"],
        "designer": ["Versace", "Dior", "Valentino", "Prada", "Louis Vuitton", "Gucci", "Chanel", "Balenciaga", "Alexander McQueen", "Givenchy"],
        "genre": ["sci-fi", "action", "romantic comedy", "thriller", "drama", "horror", "fantasy", "musical", "historical", "animated"],
        "city": ["Los Angeles", "New York", "London", "Tokyo", "Paris", "Sydney", "Berlin", "Toronto", "Seoul", "Mexico City"],
        "controversy_topic": ["controversial social media post", "past remarks", "on-set behavior", "political stance", "casting decision", "interview comments", "failed contract negotiations", "personal life choices", "creative differences", "awards show speech"],
        "personal_topic": ["mental health journey", "family life", "career struggles", "childhood experiences", "relationship advice", "creative process", "fame challenges", "personal transformation", "work-life balance", "advocacy work"],
        "amount": ["40", "50", "60", "75", "90", "100", "120", "150", "200", "250"],
        "number": ["2", "3", "4", "5"],
        "adjective": ["groundbreaking", "disappointing", "brilliant", "overrated", "captivating", "mediocre", "mind-blowing", "unforgettable", "heartwarming", "lackluster"]
    },
    "Science": {
        "science_discovery": ["a new particle", "a novel protein", "an unknown species", "a beneficial microbe", "a fundamental force interaction", "a previously unknown asteroid", "a targeted gene therapy", "a sustainable material", "an energy-efficient process", "a quantum state property"],
        "field": ["medicine", "renewable energy", "quantum computing", "space exploration", "neuroscience", "artificial intelligence", "genomics", "materials science", "particle physics", "climate science"],
        "factor": ["sleep patterns", "gut microbiome", "social media usage", "dietary habits", "regular exercise", "environmental factors", "genetic markers", "meditation practice", "urban living", "air pollution"],
        "effect": ["cognitive performance", "longevity", "mental health outcomes", "cardiovascular health", "immune system function", "neuroplasticity", "metabolic efficiency", "stress resilience", "chronic inflammation", "gene expression"],
        "space_object": ["a supermassive black hole", "an Earth-like exoplanet", "a neutron star merger", "a distant galaxy cluster", "a near-Earth asteroid", "a dormant comet", "unusual radio signals", "a super-Earth planet", "a stellar nursery", "a white dwarf star"],
        "telescope": ["the James Webb Space Telescope", "the Event Horizon Telescope", "the Hubble Space Telescope", "the Vera C. Rubin Observatory", "the Square Kilometer Array", "NASA's TESS satellite", "the European Extremely Large Telescope", "the Chandra X-ray Observatory", "the ALMA radio telescope array", "China's FAST telescope"],
        "space_phenomenon": ["galaxy formation", "dark matter distribution", "planetary system evolution", "cosmic inflation", "gravitational waves", "interstellar medium", "star life cycles", "black hole dynamics", "dark energy effects", "extrasolar planetary atmospheres"],
        "climate_finding": ["accelerating glacial melt", "shifting ocean currents", "unprecedented biodiversity loss", "changing precipitation patterns", "extreme weather frequency", "carbon sink degradation", "polar vortex destabilization", "sea level rise acceleration", "coral reef decline", "permafrost thawing"],
        "treatment": ["a targeted immunotherapy", "a CRISPR gene therapy", "an mRNA-based vaccine", "a nanomedicine approach", "a brain-computer interface", "a personalized cancer treatment", "a novel antibiotic", "a non-invasive diagnostic tool", "a stem cell therapy", "a microbiome intervention"],
        "disease": ["cancer", "Alzheimer's", "diabetes", "autoimmune disorders", "cardiovascular disease", "rare genetic disorders", "infectious disease", "neurological conditions", "chronic respiratory disorders", "metabolic syndromes"],
        "tech_invention": ["quantum computing framework", "biomimetic robot", "carbon capture system", "neural interface", "programmable matter", "lab-grown organ", "fusion energy device", "biodegradable electronic", "artificial photosynthesis system", "self-healing material"],
        "problem": ["clean energy production", "antibiotic resistance", "food security", "water scarcity", "electronic waste", "pandemic preparedness", "biodiversity loss", "space debris", "carbon emissions", "rare earth element shortages"],
        "organism": ["extremophile bacteria", "a deep-sea creature", "a resilient plant species", "a long-lived mammal", "a social insect colony", "a parasitic fungus", "a newly classified microbe", "a genetically unique amphibian", "a symbiotic organism", "a previously undiscovered primate"],
        "biological_function": ["regenerate damaged tissue", "survive extreme conditions", "communicate across species", "process toxins efficiently", "live without oxygen", "resist multiple diseases", "adapt rapidly to new environments", "produce novel antibiotics", "photosynthesize efficiently", "decode complex environmental signals"],
        "artifact": ["settlement", "burial site", "religious temple", "stone tools", "cave paintings", "written documents", "royal tomb", "trading post", "ceremonial mask", "musical instrument"],
        "location": ["North Africa", "South America", "Southeast Asia", "Eastern Europe", "the Mediterranean", "the Arabian Peninsula", "the Arctic Circle", "the Pacific Islands", "the Himalayan region", "Central America"],
        "time_period": ["5,000 years", "10,000 years", "15,000 years", "20,000 years", "30,000 years", "40,000 years", "50,000 years", "75,000 years", "100,000 years", "200,000 years"],
        "physics_theory": ["quantum entanglement principles", "relativistic space-time effects", "string theory predictions", "quantum gravity hypothesis", "dark matter interactions", "supersymmetry models", "quantum field behaviors", "particle-wave duality", "unified force theory", "black hole information paradox resolution"],
        "environment_finding": ["microplastic contamination", "pollinator population decline", "tropical deforestation", "ocean acidification", "freshwater reserve depletion", "topsoil degradation", "invasive species spread", "urban heat island effects", "nitrogen cycle disruption", "wildlife migration pattern shifts"]
    }
}

def generate_template_tweet(account: str) -> Dict[str, Any]:
    """Generate a single mock tweet based on account type."""
    # Determine account type category
    account_category = "News"  # Default
    
    if account.lower() in ['techcrunch', 'theverge', 'wired', 'mashable', 'engadget', 'techncrunch']:
        account_category = "Tech"
    elif account.lower() in ['espn', 'bleacherreport', 'skysports', 'bbcsport', 'nbcsports', 'foxsports']:
        account_category = "Sports"
    elif account.lower() in ['variety', 'ew', 'theavclub', 'rollingstone', 'entertainment', 'hollywood']:
        account_category = "Entertainment"
    elif account.lower() in ['natgeo', 'sciencemag', 'nasa', 'newscientist', 'scientificamerican', 'discovermagazine']:
        account_category = "Science"
    
    # Select template and fill
    content = ""
    if account_category == "News":
        template = random.choice(NEWS_TEMPLATES)
        topic = random.choice(TOPICS["News"])
        content = template.format(topic=topic)
    elif account_category == "Tech":
        template = random.choice(TECH_TEMPLATES)
        content = template.format(**{k: random.choice(v) for k, v in TOPICS["Tech"].items()})
    elif account_category == "Sports":
        template = random.choice(SPORTS_TEMPLATES)
        content = template.format(**{k: random.choice(v) for k, v in TOPICS["Sports"].items()})
    elif account_category == "Entertainment":
        template = random.choice(ENTERTAINMENT_TEMPLATES)
        content = template.format(**{k: random.choice(v) for k, v in TOPICS["Entertainment"].items()})
    elif account_category == "Science":
        template = random.choice(SCIENCE_TEMPLATES)
        content = template.format(**{k: random.choice(v) for k, v in TOPICS["Science"].items()})
    
    # Generate timestamp - tweets from past 24 hours
    hours_ago = random.randint(0, 24)
    minutes_ago = random.randint(0, 59)
    timestamp = datetime.datetime.now() - datetime.timedelta(hours=hours_ago, minutes=minutes_ago)
    
    # Create mock tweet
    tweet = {
        'title': f"@{account}: {content[:50]}...",
        'summary': content,
        'source': f"Twitter/{account}",
        'link': f"https://twitter.com/{account}/status/mock{int(timestamp.timestamp())}",
        'published': timestamp.isoformat(),
        'author': f"@{account}",
        'category': account_category
    }
    
    return tweet

def generate_account_tweets(account: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Generate multiple mock tweets for a given account."""
    logger.info(f"Generating {limit} mock tweets for @{account}")
    tweets = []
    
    for i in range(limit):
        tweet = generate_template_tweet(account)
        tweets.append(tweet)
    
    return tweets

def generate_mock_content() -> List[Dict[str, Any]]:
    """Generate all mock content for all accounts."""
    all_content = []
    
    for account in args.accounts:
        tweets = generate_account_tweets(account, args.limit)
        all_content.extend(tweets)
        logger.info(f"Generated {len(tweets)} mock tweets for @{account}")
    
    # Sort by most recent
    all_content.sort(key=lambda x: x['published'], reverse=True)
    
    return all_content

def main():
    """Main function."""
    logger.info(f"Starting Twitter mock content generator for {len(args.accounts)} accounts, {args.limit} tweets each")
    
    start_time = datetime.datetime.now()
    mock_tweets = generate_mock_content()
    end_time = datetime.datetime.now()
    
    # Output JSON to stdout
    sys.stdout.write(json.dumps(mock_tweets))
    sys.stdout.flush()
    
    logger.info(f"Generated {len(mock_tweets)} mock tweets in {(end_time-start_time).total_seconds():.2f} seconds")

if __name__ == "__main__":
    main()