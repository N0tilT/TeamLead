FROM node:lts-alpine
WORKDIR /app

RUN npm install -g npm@11.4.2

COPY ./package*.json ./
RUN npm install --legacy-peer-deps
RUN npm i --save-dev @types/node  

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]