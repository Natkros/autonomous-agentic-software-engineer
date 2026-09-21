FROM node:20-slim AS builder

# Next.js inlines every NEXT_PUBLIC_* variable into the client bundle at
# `next build` time, not at container startup - setting it only as a
# runtime environment variable (as docker-compose.yml's `environment:`
# does, and as Render's env vars are available by default) has no
# effect on an already-built image. Render automatically forwards any
# environment variable configured on the service as a same-named Docker
# build ARG, so declaring it here is enough to pick it up in both
# places - docker-compose still passes it through as a real build arg
# too (see that file's `build.args`).
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

WORKDIR /app
COPY apps/web/package*.json ./
RUN npm install
COPY apps/web .
RUN npm run build

FROM node:20-slim AS runner

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD ["npm", "run", "start"]
