FROM nginx

ARG WATCHTOWER_UID
ARG WATCHTOWER_GID

# Change ownership so the default configuration can be modified.
RUN chown -R $WATCHTOWER_UID:$WATCHTOWER_GID /etc/nginx/conf.d

# Use a non-root user.
USER $WATCHTOWER_UID:$WATCHTOWER_GID
