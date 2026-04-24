FROM gradle:8.5-jdk17 AS build
WORKDIR /build
COPY build.gradle.kts settings.gradle.kts ./
RUN gradle --no-daemon build -x test --stacktrace || true
COPY src ./src
RUN gradle --no-daemon bootJar -x test --stacktrace

FROM eclipse-temurin:17-jre-alpine AS runtime
WORKDIR /app
RUN addgroup -S spring && adduser -S spring -G spring
USER spring:spring
COPY --from=build /build/build/libs/*.jar app.jar
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:8003/actuator/health | grep -q '"status":"UP"' || exit 1
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
