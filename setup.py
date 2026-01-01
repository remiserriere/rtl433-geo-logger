from setuptools import setup, find_packages

setup(
    name="rtl433-geo-logger",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "flask>=2.3.0",
        "gpsd-py3>=0.3.0",
        "folium>=0.14.0",
        "flask-cors>=4.0.0",
    ],
    python_requires=">=3.7",
    author="remiserriere",
    description="RTL433 data logger with GPS geolocation and web map interface",
    entry_points={
        "console_scripts": [
            "rtl433-logger=rtl433_geo_logger.logger:main",
            "rtl433-web=rtl433_geo_logger.web:main",
        ],
    },
)
