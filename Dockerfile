FROM ubuntu:14.04

ENV DEBIAN_FRONTEND noninteractive

# =============================================================================
# Dependencies
# =============================================================================
RUN apt-get -y update
RUN apt-get -y install git wget curl nano supervisor build-essential python-pip python-dev

# =============================================================================
# Watson IoT Cloudant Connector module dependencies
# =============================================================================
RUN pip install ibmiotf cloudant bottle


# =============================================================================
# Install IoTF Connector for Cloudant
# =============================================================================
ADD connector /opt/connector-cloudant/


# =============================================================================
# Configuration
# =============================================================================

# Configure supervisord
ADD supervisord/supervisord.conf /etc/supervisor/conf.d/supervisord.conf


# =============================================================================
# Run
# =============================================================================

CMD     ["/usr/bin/supervisord"]