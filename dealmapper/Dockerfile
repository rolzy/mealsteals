# Use an official Node runtime as the base image
FROM node:latest

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install project dependencies
RUN npm install

# Copy the rest of the application code
#COPY . .

# Make port 3000 available outside the container
EXPOSE 3000

# Run the app when the container launches
CMD ["npm", "start"]

