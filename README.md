# GitHub Public Repo Scanner

## Description

Just a simple script to pull down all public GitHub repositories. It stores the results in a CSV, which is not lookup efficient. It should be easy to change to something like SQL, but YMMV; CSV is good enough for my needs.

The script grabs all of the [properties][repo-properties] available to Repository objects. Each repository is stored as a new row in the CSV. The CSV is meant to be read in with `pandas`.

If you want all of the repositories, this will take several weeks with the user rate limit (5,000 requests per hour) and take up ~500GB of space.

## Dependencies

The script uses the public [GitHub API][api] provided by [PyGitHub]. You can download this with `pip` using the included [requirements.txt](./requirements.txt) file:

```shell
pip3 install -r requirements.txt
```

## Usage

The script accepts two optional parameters:

- `--token`: an optional argument to specify your API token.
  - If no token is set, the rate limit is 60 requests per hour. You can obtain an API token under your user settings.
- `--filename`: An optional argument to specify the filename of the CSV to write to.
  - If no filename is given, "repos.csv" will be used. If the file already exists, it'll try and pick back up where it left off from a previous run. I haven't tested this fully. Go ahead and fuzz it. 🐛
 
### Examples

```
python3 ./get-repos.py
python3 ./get-repos.py --token <my-token>
python3 ./get-repos.py --filename repos.csv
python3 ./get-repos.py --token <my-token> --filename repos.csv
```

## FAQ

### Why not use [GH Archive][gharchive]?

I wanted to do it myself and learn the API. You probably want the GH Archive, not my messy script.

[repo-properties]: https://pygithub.readthedocs.io/en/latest/github_objects/Repository.html
[api]: https://docs.github.com/en/rest
[PyGitHub]: https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwi_lKT4kf3_AhWjElkFHc_kDDoQFnoECA8QAQ&url=https%3A%2F%2Fgithub.com%2FPyGithub%2FPyGithub&usg=AOvVaw1eqHebNW1jhUVYKA0lhzO4&opi=89978449
[gharchive]: https://www.gharchive.org/
