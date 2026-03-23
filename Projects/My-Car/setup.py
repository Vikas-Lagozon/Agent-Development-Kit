from setuptools import setup, find_packages

setup(
    name='my_car',
    version='0.1.0',
    packages=find_packages(where='app'),
    package_dir={'': 'app'},
    install_requires=[
        'fastapi==0.111.1',
        'uvicorn[standard]==0.30.1',
        'sqlalchemy[asyncio]==2.0.31',
        'aiosqlite==0.20.0',
        'alembic==1.13.2',
        'PyJWT==2.8.0',
        'passlib[bcrypt]==1.7.4',
        'python-multipart==0.0.9',
        'pydantic==2.8.2',
        'pydantic-settings==2.3.4',
        'email-validator==2.2.0',
        'python-dotenv==1.0.1',
        'httpx==0.27.0',
        'aiomysql==0.2.0',
    ],
    entry_points={
        'console_scripts': [
            'mycar=app.main:main',  # If you have a main function in app/main.py
        ],
    },
    author='Your Name',
    author_email='your.email@example.com',
    description='A FastAPI project',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='http://example.com',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)
