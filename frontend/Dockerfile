FROM node:20-alpine

WORKDIR /app

# Copy dependency definitions
COPY package*.json ./

# Install npm dependencies
RUN npm install

# Copy application sources
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
