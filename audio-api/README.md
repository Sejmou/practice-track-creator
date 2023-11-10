# Audio Processing API
A fairly basic API for audio processing. At this moment, it has one endpoint:
- `practice_tracks`: accepts $n$ mp3 files (at least 2) and creates combined "practice tracks" from them. $n$ practice tracks are created, each with one of the given tracks being 'highlighted' (louder than the rest). Additionally, a regular mix of all input tracks is included.

## Run
To run the API, you need to have [Docker](https://www.docker.com/) installed. Then, run the following command in the root directory of the project:
```
docker compose up
```

## Usage
Refer to the SvelteKit app (in `webapp` sibling directory of this repo)