#!/usr/bin/env bash
# ============================================================
# ForgeOps Nexus Seeder
# Seeds the Nexus offline mirror with vast common Java libraries
# (Spring Boot, Database drivers, Testing frameworks, etc.)
# ============================================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${CYAN}[$(date '+%H:%M:%S')] [SEED]${NC} $*"; }
success() { echo -e "${GREEN}[$(date '+%H:%M:%S')] [✅ OK]${NC} $*"; }

log "Creating a temporary dummy project to seed dependencies..."
SEED_DIR=$(mktemp -d)
cd "${SEED_DIR}"

# 1. Create a dummy Spring Boot POM with vast dependencies
cat << 'EOF' > pom.xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.3.5</version>
        <relativePath/> <!-- lookup parent from repository -->
    </parent>
    <groupId>local.forgeops</groupId>
    <artifactId>nexus-seed</artifactId>
    <version>1.0.0</version>
    <name>nexus-seed</name>
    <description>Dummy project to populate Nexus cache</description>
    
    <properties>
        <java.version>17</java.version>
    </properties>

    <dependencies>
        <!-- Spring Boot Core / Web -->
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-thymeleaf</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-data-jpa</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-security</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-validation</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-actuator</artifactId></dependency>
        
        <!-- Databases -->
        <dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId></dependency>
        <dependency><groupId>com.mysql</groupId><artifactId>mysql-connector-j</artifactId></dependency>
        <dependency><groupId>com.h2database</groupId><artifactId>h2</artifactId></dependency>
        
        <!-- Utilities -->
        <dependency><groupId>org.projectlombok</groupId><artifactId>lombok</artifactId><optional>true</optional></dependency>
        <dependency><groupId>org.mapstruct</groupId><artifactId>mapstruct</artifactId><version>1.5.5.Final</version></dependency>
        <dependency><groupId>com.fasterxml.jackson.core</groupId><artifactId>jackson-databind</artifactId></dependency>
        
        <!-- Testing -->
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-test</artifactId><scope>test</scope></dependency>
        <dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId><scope>test</scope></dependency>
        <dependency><groupId>org.mockito</groupId><artifactId>mockito-core</artifactId><scope>test</scope></dependency>
    </dependencies>
</project>
EOF

# 2. Create settings.xml pointing to local Nexus
cat << 'EOF' > settings.xml
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0 https://maven.apache.org/xsd/settings-1.0.0.xsd">
    <mirrors>
        <mirror>
            <id>forgeops-nexus-mirror</id>
            <name>ForgeOps Local Nexus Mirror</name>
            <!-- Using localhost assuming this script is run on the host where Nexus port 8081 is mapped -->
            <url>http://localhost:8081/repository/forgeops-maven-mirror/</url>
            <mirrorOf>*</mirrorOf>
        </mirror>
    </mirrors>
</settings>
EOF

log "Starting Maven dependency download to seed Nexus..."
log "Make sure Nexus is running and online for this step!"

# We use docker to run maven so the host doesn't need maven installed
# Using --network host so localhost:8081 routes to the Nexus container mapped to the host
docker run --rm \
    --network host \
    -v "${SEED_DIR}:/app" \
    -w /app \
    maven:3.9-eclipse-temurin-17 \
    mvn dependency:go-offline -s settings.xml

success "Nexus successfully seeded with vast dependency libraries!"

log "Cleaning up temporary files..."
rm -rf "${SEED_DIR}"
success "Cleanup complete."
