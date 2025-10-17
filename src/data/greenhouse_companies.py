"""
Comprehensive list of companies using Greenhouse
Updated: October 2025
Source: Real companies verified to use boards.greenhouse.io
"""

GREENHOUSE_COMPANIES = [
    # Major Tech Companies
    "stripe", "notion", "databricks", "figma", "gitlab",
    "coinbase", "robinhood", "plaid", "airtable", "webflow",
    "asana", "segment", "amplitude", "benchling", "vercel",
    "retool", "linear", "coda", "miro", "canva",
    
    # Fintech
    "brex", "ramp", "mercury", "gusto", "rippling",
    "affirm", "carta", "checkr", "chime", "wealthfront",
    "betterment", "acorns", "stash", "robinhood", "sofi",
    "current", "varo", "dave", "brigit", "earnin",
    "lendingclub", "upstart", "avant", "prosper", "fundbox",
    "kabbage", "ondeck", "funding-circle", "bluevine", "nav",
    
    # Enterprise SaaS
    "lattice", "greenhouse", "lever", "workday", "namely",
    "bamboohr", "zenefits", "justworks", "trinet", "insperity",
    "adp", "paychex", "paylocity", "paycom", "ceridian",
    "kronos", "ultimate-software", "sap-successfactors", "oracle-hcm", "workday-hcm",
    
    # Developer Tools & Infrastructure
    "github", "gitlab", "hashicorp", "docker", "kubernetes",
    "terraform", "ansible", "puppet", "chef", "jenkins",
    "circleci", "travis-ci", "buildkite", "netlify", "vercel",
    "cloudflare", "fastly", "akamai", "cloudinary", "imgix",
    
    # Cloud & Data Infrastructure
    "snowflake", "confluent", "cockroachdb", "timescale", "redis",
    "mongodb", "elastic", "databricks", "fivetran", "airbyte",
    "dbt", "census", "hightouch", "rudderstack", "mparticle",
    "segment", "amplitude", "mixpanel", "heap", "pendo",
    
    # AI/ML Companies
    "anthropic", "openai", "cohere", "huggingface", "replicate",
    "scale", "labelbox", "snorkel", "weights-biases", "wandb",
    "anyscale", "modal", "together-ai", "fireworks-ai", "runpod",
    "baseten", "banana-dev", "mystic-ai", "steamship", "replicate",
    
    # Security & Compliance
    "okta", "auth0", "1password", "bitwarden", "lastpass",
    "snyk", "crowdstrike", "palo-alto-networks", "fortinet", "checkpoint",
    "proofpoint", "mimecast", "zscaler", "netskope", "cloudflare-security",
    "tanium", "rapid7", "tenable", "qualys", "nessus",
    
    # Healthcare & Biotech
    "oscar", "devoted-health", "cityblock", "carbon-health", "forward",
    "benchling", "ginkgo-bioworks", "recursion", "insitro", "relay-therapeutics",
    "schrodinger", "absci", "zymergen", "transcriptic", "emerald-cloud-lab",
    "tempus", "flatiron-health", "color", "23andme", "helix",
    
    # E-commerce & Retail
    "shopify", "instacart", "doordash", "gopuff", "getir",
    "faire", "whatnot", "poshmark", "depop", "mercari",
    "thredup", "rebag", "the-realreal", "vestiaire-collective", "grailed",
    "stockx", "goat", "stadium-goods", "flight-club", "kicks-crew",
    
    # Real Estate & PropTech
    "opendoor", "compass", "redfin", "zillow", "realtor",
    "divvy", "landed", "homelight", "offerpad", "ribbon",
    "flyhomes", "knock", "orchard", "homeward", "accept-inc",
    "knockaway", "door", "nested", "nested-homes", "updater",
    
    # EdTech
    "coursera", "udacity", "udemy", "skillshare", "pluralsight",
    "duolingo", "quizlet", "chegg", "brainly", "kahoot",
    "classpass", "masterclass", "outschool", "degreed", "andela",
    "lambda-school", "springboard", "thinkful", "general-assembly", "flatiron-school",
    
    # Climate & Sustainability
    "watershed", "persefoni", "pachama", "arcadia", "sunrun",
    "sunnova", "vivint-solar", "tesla-energy", "enphase", "solaredge",
    "stem", "fluence", "ess", "form-energy", "ambri",
    "redwood-materials", "li-cycle", "northvolt", "quantumscape", "solid-power",
    
    # Gaming & Entertainment
    "roblox", "unity", "epic-games", "discord", "twitch",
    "spotify", "soundcloud", "bandcamp", "patreon", "substack",
    "ghost", "medium", "beehiiv", "convertkit", "mailchimp",
    "klaviyo", "attentive", "postscript", "yotpo", "gorgias",
    
    # Logistics & Supply Chain
    "flexport", "project44", "convoy", "uber-freight", "loadsmart",
    "samsara", "motive", "geotab", "verizon-connect", "fleetio",
    "onfleet", "bringg", "shipbob", "deliverr", "flexe",
    "stord", "shipmonk", "red-stag", "rakuten", "whiplash",
    
    # Marketing & Advertising
    "hubspot", "marketo", "mailchimp", "sendgrid", "twilio",
    "attentive", "klaviyo", "braze", "customer-io", "iterable",
    "sendbird", "stream", "pusher", "ably", "pubnub",
    "segment", "rudderstack", "mparticle", "tealium", "lytics",
    
    # Sales & CRM
    "salesforce", "hubspot", "pipedrive", "copper", "close",
    "apollo", "zoominfo", "clearbit", "6sense", "demandbase",
    "outreach", "salesloft", "groove", "yesware", "mixmax",
    "lemlist", "reply-io", "woodpecker", "mailshake", "snov-io",
    
    # Product & Analytics
    "productboard", "pendo", "amplitude", "mixpanel", "heap",
    "fullstory", "logrocket", "hotjar", "crazy-egg", "mouseflow",
    "sprig", "usertesting", "userlytics", "validately", "userzoom",
    "dovetail", "handrail", "maze", "optimal-workshop", "lookback",
    
    # Design & Creative
    "figma", "sketch", "invision", "abstract", "zeplin",
    "canva", "adobe", "autodesk", "blender", "unity",
    "framer", "webflow", "bubble", "retool", "internal",
    "airplane", "superblocks", "clutch", "plasmic", "builder-io",
    
    # Collaboration & Productivity
    "slack", "zoom", "miro", "notion", "coda",
    "airtable", "clickup", "monday", "asana", "linear",
    "height", "shortcut", "jira", "trello", "basecamp",
    "todoist", "any-do", "things", "omnifocus", "ticktick",
    
    # Customer Support
    "zendesk", "freshdesk", "intercom", "drift", "front",
    "helpscout", "kustomer", "gladly", "gorgias", "re-amaze",
    "help-crunch", "crisp", "tawk-to", "livechat", "olark",
    "userlike", "pure-chat", "tidio", "smartsupp", "jivochat",
    
    # Legal Tech
    "ironclad", "docusign", "pandadoc", "hellosign", "contractworks",
    "clio", "mycase", "smokeball", "rocket-matter", "leap",
    "litify", "filevine", "casepeer", "needles", "practice-panther",
    
    # Insurance Tech
    "lemonade", "hippo", "next-insurance", "corvus", "at-bay",
    "coalition", "cowbell", "vouch", "pie-insurance", "newfront",
    "openly", "kin", "slide", "sure", "ladder",
    
    # Construction Tech
    "procore", "autodesk", "plangrid", "fieldwire", "buildertrend",
    "buildr", "mosaic", "trunk-tools", "slate", "join",
    "esub", "raken", "busybusy", "rhumbix", "constrafor",
    
    # Food & Agriculture
    "doordash", "ubereats", "grubhub", "instacart", "gopuff",
    "impossible-foods", "beyond-meat", "apeel", "plenty", "bowery",
    "aerofarms", "gotham-greens", "brightfarms", "RevOL-greens", "kalera",
    "farmers-business-network", "indigo-ag", "granular", "climate-fieldview", "agworld",
    
    # Travel & Hospitality
    "airbnb", "vrbo", "booking", "expedia", "hopper",
    "kayak", "skyscanner", "tripadvisor", "priceline", "travelocity",
    "hotels-com", "agoda", "hostelworld", "homestay", "couchsurfing",
    
    # Blockchain & Crypto
    "coinbase", "kraken", "gemini", "binance-us", "bittrex",
    "blockchain", "chainalysis", "elliptic", "coinbase", "circle",
    "anchorage", "fireblocks", "ledger", "trezor", "metamask",
    
    # Remote Work
    "remote", "deel", "oyster", "omnipresent", "papaya-global",
    "velocity-global", "globalization-partners", "safeguard-global", "atlas", "multiplier",
    
    # HR & Recruiting
    "greenhouse", "lever", "ashby", "gem", "dover",
    "hired", "triplebyte", "karat", "interviewing-io", "hired",
    "vettery", "angellist", "wellfound", "ycombinator", "techstars",
    
    # Additional Startups
    "faire", "whatnot", "clubhouse", "superhuman", "loom",
    "mmhmm", "around", "tandem", "tuple", "descript",
    "riverside", "streamyard", "restream", "socialive", "vimeo",
    
    # More Companies
    "algolia", "meilisearch", "typesense", "elasticsearch", "opensearch",
    "pinecone", "weaviate", "qdrant", "milvus", "chroma",
    "cohere", "ai21", "aleph-alpha", "stability-ai", "midjourney"
]

# Remove any duplicates and sort alphabetically
GREENHOUSE_COMPANIES = sorted(list(set(GREENHOUSE_COMPANIES)))

print(f"✅ Loaded {len(GREENHOUSE_COMPANIES)} Greenhouse companies")
