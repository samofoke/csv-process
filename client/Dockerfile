FROM node:22.18.0-alpine as build

WORKDIR /app

# copy and install dependecies.
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
