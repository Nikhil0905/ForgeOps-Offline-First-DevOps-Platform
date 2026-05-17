FROM jenkins/jenkins:lts-jdk17

USER root

# Install Docker CLI
RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
       https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Install Maven
RUN apt-get update && apt-get install -y maven && rm -rf /var/lib/apt/lists/*

# Add SSL certificates for proxy/firewall trust (Sophos)
COPY cert-*.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates

# Add jenkins user to docker group
RUN groupadd -f docker && usermod -aG docker jenkins

# Install Jenkins plugins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Pre-configure Maven settings for the jenkins user
RUN mkdir -p /var/jenkins_home/.m2
COPY settings.xml /var/jenkins_home/.m2/settings.xml
RUN chown -R jenkins:jenkins /var/jenkins_home/.m2

# Install JCasC config
ENV CASC_JENKINS_CONFIG=/var/jenkins_home/casc_configs/jenkins.yaml
RUN mkdir -p /var/jenkins_home/casc_configs

USER jenkins

# Skip setup wizard
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"
