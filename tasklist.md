# tasklist.md - GlovePost Development Tasks (Updated March 09, 2025)

## Content Aggregation
- **Completed:**
  - [x] Implement RSS feed parser in Python
  - [x] Set up content categorization based on keywords
  - [x] Store content in MongoDB with proper schema
  - [x] Add content refresh script to update database with fresh content
  - [x] Implement content sorting by timestamp
  - [x] Implement web scraping for X/Twitter content (no paid API)
    - [x] Use `beautifulsoup4` to scrape public X pages (e.g., news accounts)
    - [x] Parse tweets for `title`, `content_summary`, `url`, `timestamp`
    - [x] Add fallback to Nitter instances for more reliable scraping
  - [x] Implement web scraping for Facebook content
    - [x] Scrape public Facebook pages (e.g., news outlets) using `requests` and `beautifulsoup4`
    - [x] Handle basic content extraction (posts, links)
    - [x] Add fallback to mbasic.facebook.com mobile version
  - [x] Add additional media sources through combined RSS and web scraping
  - [x] Improve content filtering:
    - [x] Add duplicate detection (e.g., URL, title matching, content similarity)
    - [x] Enhance quality filter (e.g., minimum word count, spam keyword blacklist)
    - [x] Implement advanced filtering algorithms to strip away noise and fluff
    - [x] Develop heuristic rules to identify and remove low-quality content (e.g., clickbait, ads)
- **Pending:**
  - [ ] Integrate more advanced natural language processing (NLP) techniques to assess content relevance and quality
  - [ ] Implement tracking of source reliability and content quality over time
  - [ ] Add support for image content analysis and extraction
  - [ ] Create a scheduler for periodic content updates
- **New Tasks (4chan and Reddit Integration):**
  - [ ] Implement web scraping for 4chan content
    - [ ] Use `requests` and `beautifulsoup4` to scrape threads from public 4chan boards (e.g., /g/, /news/)
    - [ ] Parse posts for `title` (thread subject), `content_summary` (post text), `url` (thread link), `timestamp`
    - [ ] Handle anonymous posting by assigning a generic source (e.g., "4chan")
  - [ ] Implement web scraping for Reddit content
    - [ ] Use `requests` and `beautifulsoup4` to scrape public subreddits (e.g., r/news, r/technology)
    - [ ] Parse posts for `title`, `content_summary` (self-text or link description), `url`, `timestamp`
    - [ ] Avoid Reddit API to keep costs down, relying on scraping within legal bounds
- **New Tasks (from Research - Search Functionality):**
  - [ ] Set up indexing for efficient searching
    - [ ] Use MongoDB text search or integrate ElasticSearch for advanced search capabilities
    - [ ] Index content fields like `title`, `content_summary`, and `category` for full-text search

## Recommendation Engine
- **Completed:**
  - [x] Create Python-based recommendation engine
  - [x] Implement category-based content recommendations
  - [x] Connect recommendation engine to MongoDB for content retrieval
  - [x] Add basic scoring algorithm for content relevance
  - [x] Set up integration between Node.js backend and Python engine
  - [x] Create virtual environment for Python dependencies
  - [x] Add reasoning for recommendations ("Recommended because...")
  - [x] Enhance recommendation algorithm with more sophisticated scoring
    - [x] Add time decay factor (recent content scores higher)
  - [x] Add user interaction history to recommendation calculations
    - [x] Fetch interactions from PostgreSQL
  - [x] Implement keyword-based recommendations
    - [x] Extract keywords from content summaries
    - [x] Match with user-defined keywords in preferences
  - [x] Integrate thumbs up/thumbs down feedback into recommendation engine
    - [x] Update `recommendation_engine.py` to factor in user ratings
    - [x] Adjust content scores based on aggregated user feedback across all users
  - [x] Develop a user interface for tweaking recommendation parameters
    - [x] Add slider for users to adjust rating influence on recommendations
    - [x] Provide information explaining how the rating weight affects recommendations
  - [x] Implement a feedback loop where user interactions directly influence future recommendations
    - [x] Adjust recommendation scores based on user feedback (likes/dislikes)
- **Pending:**
  - [ ] Incorporate source reputation (e.g., weight trusted sources higher)
  - [ ] Add content diversity features to avoid recommendation bubbles
    - [ ] Ensure variety by limiting same-category recommendations (e.g., max 3 per category)
- **New Tasks (from Research):**
  - [ ] Create a visualization of the recommendation process to enhance transparency
    - [ ] Display a breakdown of why each article was recommended (e.g., "60% category match, 30% source preference, 10% recency")
    - [ ] Provide an interactive chart or graph showing how user preferences influence recommendations
  - [ ] Allow users to exclude certain topics or sources from recommendations
- **New Tasks (from Research - Commenting and Search):**
  - [ ] Integrate comment analysis into recommendation algorithm
    - [ ] Extract keywords or sentiment from comments using NLP (e.g., NLTK or spaCy)
    - [ ] Adjust recommendation scores based on comment activity (e.g., highly discussed articles score higher)
  - [ ] Use search queries to influence recommendations
    - [ ] Log search queries and suggest related articles based on search history
    - [ ] Adjust recommendation scores for frequently searched articles with a decay factor

## User Management
- **Completed:**
  - [x] Implement user preferences storage
  - [x] Create PostgreSQL integration for user data
  - [x] Add user consent tracking for privacy controls
  - [x] Implement API for updating user preferences
- **Pending:**
  - [ ] Add user authentication (OAuth 2.0)
    - [ ] Install `passport` and `passport-google-oauth20`
    - [ ] Configure Google OAuth in `server.js`
    - [ ] Secure endpoints with middleware
  - [ ] Implement user registration and login functionality
    - [ ] Add `POST /auth/register` and `POST /auth/login` endpoints
    - [ ] Store hashed passwords in PostgreSQL (using `bcrypt`)
  - [ ] Create user profile pages
    - [ ] Add API endpoint `GET /user/profile/:id`
- **New Tasks (from Research):**
  - [ ] Allow users to influence and tweak the recommendation algorithm
    - [ ] Expose algorithm parameters in the user settings (e.g., weight sliders for different factors)
    - [ ] Provide clear documentation or tooltips explaining how each parameter affects recommendations
- **New Tasks (from Research - Commenting System):**
  - [ ] Implement comment moderation tools
    - [ ] Allow admins to delete/flag comments via `GET /admin/comments`
    - [ ] Implement reporting system (`POST /comments/report`) with admin notifications

## User Interactions
- **Completed:**
  - [x] Create interaction tracking system (views, clicks, etc.)
  - [x] Implement interaction recording in PostgreSQL
  - [x] Add API endpoints for retrieving user interaction history
  - [x] Support clearing interaction history for privacy
  - [x] Add thumbs up/thumbs down tracking to user interactions
    - [x] Extend `interactions` table in PostgreSQL with `rating` column
    - [x] Update `POST /interactions` endpoint to accept rating data
- **Pending:**
  - None (fully completed based on status)
- **New Tasks (from Research - Commenting System):**
  - [ ] Implement commenting system
    - [ ] Create PostgreSQL table for comments (`comment_id`, `user_id`, `article_id`, `comment_text`, `timestamp`)
    - [ ] Implement API endpoints: `POST /comments`, `GET /comments/article/:id`

## Frontend
- **Completed:**
  - [x] Create basic React application structure
  - [x] Implement Home page with content display
  - [x] Add Settings page for user preferences
  - [x] Create ContentCard component for displaying articles
  - [x] Connect frontend to backend API endpoints
  - [x] Add basic styling and layout
  - [x] Improve mobile responsiveness
    - [x] Add media queries in `index.css`, `App.css`, `Home.css`, and `Settings.css`
    - [x] Test on multiple device sizes
  - [x] Add content filtering by category/source in UI
    - [x] Create filter dropdowns in `Home.js`
    - [x] Update API calls with query params
  - [x] Add user feedback mechanism for recommendations
    - [x] Add "Like/Dislike" (thumbs up/down) buttons to `ContentCard`
    - [x] Send feedback to interaction endpoint
- **Pending:**
  - [ ] Add dark mode theme
    - [ ] Implement theme toggle in `App.js`
    - [ ] Define dark mode styles in `index.css`
  - [ ] Implement more sophisticated UI with glove/post imagery
    - [ ] Add SVG icons for gloves and posts
    - [ ] Style `ContentCard` to resemble gloves on posts
  - [ ] Create detailed article view page
    - [ ] Add `Article.js` component
    - [ ] Route to `/article/:url` with full content display
- **New Tasks (from Research):**
  - [ ] Design the UI with the glove-on-post metaphor
    - [ ] Use glove icons to represent articles and posts to represent categories
    - [ ] Create an animated or interactive element where users can "pick up" gloves (articles) from posts
  - [ ] Implement a "Lost and Found" section for user-saved articles
    - [ ] Allow users to save articles for later, inspired by finding lost gloves
- **New Tasks (Thumbs Up/Down Mechanism):**
  - [x] Add thumbs up/thumbs down buttons to `ContentCard` component
    - [x] Include icons for thumbs-up/down
    - [x] Send rating data to `POST /interactions` on click
  - [x] Display aggregated thumbs up/down counts on each post
    - [x] Fetch ratings from backend and show totals in UI
- **New Tasks (from Research - Commenting, Search, Accessibility):**
  - [ ] Add comment section to `Article.js` component
    - [ ] Display comments sorted by timestamp with user info
    - [ ] Add form for posting comments with validation
  - [ ] Implement search bar in `App.js` or `Home.js`
    - [ ] Add search input with autocomplete using `react-autosuggest`
    - [ ] Create `SearchResults.js` component for displaying results with pagination
  - [ ] Ensure all images have alt text
    - [ ] Add descriptive alt text to glove/post imagery and other images
    - [ ] Verify compliance with tools like WAVE or axe
  - [ ] Check and adjust color contrast for readability
    - [ ] Ensure WCAG contrast ratios (e.g., 4.5:1) in light and dark modes
    - [ ] Use `color-contrast` library for checks
  - [ ] Make site navigable using keyboard only
    - [ ] Ensure all interactive elements are focusable with `tabindex` and ARIA roles
    - [ ] Test with screen readers (e.g., NVDA, JAWS)
  - [ ] Provide clear labels and instructions for forms
    - [ ] Add `aria-label` and `aria-describedby` to forms (search, comments)
    - [ ] Include inline help text for complex inputs

## Infrastructure
- **Completed:**
  - None (no infrastructure tasks marked complete in status)
- **Pending:**
  - [ ] Set up automated testing
    - [ ] Install Jest in `backend` and `frontend`
    - [ ] Write unit tests for `content.js`, `user.js`, `recommendations.js`
    - [ ] Test frontend components (`Home`, `Settings`)
  - [ ] Configure production deployment
    - [ ] Build frontend (`npm run build`)
    - [ ] Serve via `backend/public` in `server.js`
    - [ ] Deploy to AWS with PM2
  - [ ] Implement caching for faster load times
    - [ ] Use Redis for content caching (`/content/latest`)
    - [ ] Cache recommendations for 1 hour
  - [ ] Set up monitoring and logging
    - [ ] Install Winston or Morgan for logging
    - [ ] Set up basic monitoring (e.g., uptime checks)
  - [ ] Optimize performance for high traffic
    - [ ] Conduct load testing with 1,000 concurrent users
  - [ ] Implement rate limiting for API endpoints
    - [ ] Use `express-rate-limit` to prevent abuse
- **New Tasks (from Research - Analytics):**
  - [ ] Integrate Google Analytics or similar tool
    - [ ] Set up Google Analytics for page views, sessions, and bounce rates
    - [ ] Configure events for key actions (e.g., article views, searches, comments)
  - [ ] Set up custom events for key user actions
    - [ ] Track "Article Viewed," "Comment Posted," "Search Performed" events
    - [ ] Store aggregated analytics in a separate database for reporting

## Next Steps Priority
1. **Implement User Authentication (OAuth 2.0)**
   - Essential for personalization and security, supports proper user identification
   - High priority as it affects multiple features (comments, profiles) and user experience
   - Will enable proper user profile management and secure data access

2. **Add Dark Mode Theme**
   - Improve accessibility and user experience, especially for nighttime reading
   - Relatively quick win with high user satisfaction impact
   - Will complete the core UI improvement tasks we started

3. **Implement the Glove-on-Post Visual Metaphor**
   - Create a distinct visual identity for the application
   - Design and implement custom SVG icons for the metaphor
   - Style ContentCard components to match the metaphor

4. **Create Detailed Article View Page**
   - Add a dedicated page for viewing full article details
   - Improve user experience for content consumption
   - Enable more detailed interaction with content

5. **Set Up Automated Testing**
   - Ensures code quality and prevents regressions
   - Will be especially important before tackling larger features

## Additional Notes
- **Research Integration:** New tasks enhance GlovePost's core concepts: aggregating diverse sources (now including 4chan and Reddit), filtering out noise, personalizing recommendations with comments and search data, and embedding the glove-on-post metaphor.
- **Scraping Compliance:** Web scraping for X/Twitter, Facebook, 4chan, and Reddit must comply with their terms of service and robots.txt files. Fallbacks (e.g., Nitter, mbasic.facebook.com) improve reliability.
- **User Empowerment:** Thumbs up/down, commenting, search, and parameter tweaking provide robust tools for user control and engagement.
- **Thematic Design:** The glove-on-post metaphor remains central, with potential to tie thumbs up/down and comments into the UI (e.g., "raising" good content, "lowering" bad content, "sharing found gloves").
- **Accessibility and Analytics:** New tasks ensure inclusivity and data-driven improvements, aligning with best practices for aggregation websites.