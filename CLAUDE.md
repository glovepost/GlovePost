# GlovePost Development Guidelines

## Build & Test Commands
### Frontend (React)
- Start frontend: `cd frontend/glovepost-ui && npm start`
- Build frontend: `cd frontend/glovepost-ui && npm run build`
- Test frontend: `cd frontend/glovepost-ui && npm test`
- Test single component: `cd frontend/glovepost-ui && npm test -- -t "test name"`

### Backend (Node.js)
- Start backend: `cd backend && npm run start`
- Dev backend: `cd backend && npm run dev`
- Test backend: `cd backend && npm test`

### Python Scripts
- Run content refresh: `cd scripts && ./refresh_content.sh`
- Run specific scrapers: `cd scripts && ./refresh_content.sh --scrapers=reddit,twitter`
- Run recommendations: `cd scripts && python scripts/recommendation_engine.py`

## Code Style Guidelines
- **Formatting**: 2-space indentation, Prettier for JS/TS, Black for Python
- **Naming**: camelCase (variables/functions), PascalCase (components/classes)
- **Imports**: Group imports (React, third-party, local) with blank lines
- **Components**: Functional components with hooks, modular file structure
- **Error Handling**: Try/catch for async ops, proper error propagation
- **Types**: Explicit TypeScript, avoid `any`
- **API Calls**: Async/await with proper loading/error states
- **CSS**: CSS modules for component styling
- **Testing**: Jest with React Testing Library for frontend, Jest for backend