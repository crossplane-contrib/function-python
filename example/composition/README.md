# Example manifests

You can run your function locally and test it using `crossplane render`
with these example manifests.

```shell
# Run the function locally
$ hatch run development
```

```shell
# Then, in another terminal, call it with these example manifests
$ crossplane beta render xr.yaml composition.yaml functions.yaml -r
```