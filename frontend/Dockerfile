FROM node:lts-alpine
ENV NODE_ENV=development
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm install --silent
COPY . .
EXPOSE 5173
RUN chown -R node /usr/src/app
USER node
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
