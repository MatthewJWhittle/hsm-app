# Firebase Emulator Suite (Firestore + Auth). firebase-tools requires JDK 21+ for emulators.
FROM eclipse-temurin:21-jre-noble

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g firebase-tools@15.12.0

WORKDIR /workspace

CMD ["firebase", "emulators:start", "--only", "firestore,auth", "--project", "hsm-dashboard"]
