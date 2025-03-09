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

## Recommendation Engine
- **Completed:**
  - [x] Create Python-based recommendation engine
  - [x] Implement category-based content recommendations
  - [x] Connect recommendation engine to MongoDB for content retrieval
  - [x] Add basic scoring algorithm for content relevance
  - [x] Set up integration between Node.js backend and Python engine
  - [x] Create virtual environment for Python dependencies
  - [x] Add reasoning for recommendations ("Recommended because...")
- **Pending:**
  - [ ] Enhance recommendation algorithm with more sophisticated scoring
    - [ ] Add time decay factor (recent content scores higher)
    - [ ] Incorporate source reputation (e.g., weight trusted sources higher)
  - [ ] Add user interaction history to recommendation calculations
    - [ ] Fetch interactions from PostgreSQL
    - [ ] Adjust scores based on views/clicks
  - [ ] Implement keyword-based recommendations
    - [ ] Extract keywords from content summaries
    - [ ] Match with user-defined keywords in preferences
  - [ ] Add content diversity features to avoid recommendation bubbles
    - [ ] Ensure variety by limiting same-category recommendations (e.g., max 3 per category)
- **New Tasks (from Research):**
  - [ ] Develop a user interface for tweaking recommendation parameters
    - [ ] Add sliders or input fields for users to adjust topic weights, source preferences, and recency importance
    - [ ] Allow users to exclude certain topics or sources
  - [ ] Create a visualization of the recommendation process to enhance transparency
    - [ ] Display a breakdown of why each article was recommended (e.g., "60% category match, 30% source preference, 10% recency")
    - [ ] Provide an interactive chart or graph showing how user preferences influence recommendations
  - [ ] Implement a feedback loop where user interactions directly influence future recommendations
    - [ ] Adjust recommendation scores based on user feedback (e.g., likes, dislikes, "not interested")

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
  - [ ] Add email notifications for new content
    - [ ] Install `nodemailer`
    - [ ] Send emails based on user preferences
- **New Tasks (from Research):**
  - [ ] Allow users to influence and tweak the recommendation algorithm
    - [ ] Expose algorithm parameters in the user settings (e.g., weight sliders for different factors)
    - [ ] Provide clear documentation or tooltips explaining how each parameter affects recommendations

## User Interactions
- **Completed:**
  - [x] Create interaction tracking system (views, clicks, etc.)
  - [x] Implement interaction recording in PostgreSQL
  - [x] Add API endpoints for retrieving user interaction history
  - [x] Support clearing interaction history for privacy
- **Pending:**
  - None (fully completed based on status)

## Frontend
- **Completed:**
  - [x] Create basic React application structure
  - [x] Implement Home page with content display
  - [x] Add Settings page for user preferences
  - [x] Create ContentCard component for displaying articles
  - [x] Connect frontend to backend API endpoints
  - [x] Add basic styling and layout
- **Pending:**
  - [ ] Improve mobile responsiveness
    - [ ] Add media queries in `index.css`
    - [ ] Test on multiple device sizes
  - [ ] Add dark mode theme
    - [ ] Implement theme toggle in `App.js`
    - [ ] Define dark mode styles in `index.css`
  - [ ] Implement more sophisticated UI with glove/post imagery
    - [ ] Add SVG icons for gloves and posts
    - [ ] Style `ContentCard` to resemble gloves on posts
  - [ ] Add content filtering by category/source in UI
    - [ ] Create filter dropdowns in `Home.js`
    - [ ] Update API calls with query params (e.g., `/content/latest?category=tech`)
  - [ ] Create detailed article view page
    - [ ] Add `Article.js` component
    - [ ] Route to `/article/:url` with full content display
  - [ ] Add user feedback mechanism for recommendations
    - [ ] Add "Like/Dislike" buttons to `ContentCard`
    - [ ] Send feedback to new endpoint `POST /feedback`
- **New Tasks (from Research):**
  - [ ] Design the UI with the glove-on-post metaphor
    - [ ] Use glove icons to represent articles and posts to represent categories
    - [ ] Create an animated or interactive element where users can "pick up" gloves (articles) from posts
  - [ ] Implement a "Lost and Found" section for user-saved articles
    - [ ] Allow users to save articles for later, inspired by finding lost gloves

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

## Next Steps Priority
1. **Implement User Authentication (OAuth 2.0)**
   - Essential for personalization and security
2. **Enhance Recommendation Algorithm with Interaction History and Advanced Filtering**
   - Incorporates user feedback, interaction data, and improved noise reduction
3. **Add Web Scraping for X/Twitter and Facebook**
   - Expands content sources without relying on paid APIs
4. **Improve Frontend UX/UI with Glove-on-Post Imagery and Mobile Responsiveness**
   - Enhances user engagement with thematic design and better accessibility
5. **Set Up Automated Testing**
   - Ensures code quality and prevents regressions

## Additional Notes
- **Research Integration:** New tasks enhance GlovePost’s core concepts: aggregating diverse sources, filtering out noise, personalizing recommendations, and embedding the glove-on-post metaphor into the UI/UX.
- **Scraping Compliance:** Web scraping for X/Twitter and Facebook must comply with their terms of service and robots.txt files. Alternative open data sources (e.g., public RSS feeds) may be considered if needed.
- **User Empowerment:** Features like tweaking recommendation parameters and visualizing the recommendation process give users more control and transparency.
- **Thematic Design:** The glove-on-post metaphor is woven into the frontend tasks to create a unique and engaging user experience.