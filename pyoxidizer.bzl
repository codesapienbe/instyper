python_config = PythonConfig()
packaging_policy = PackagingPolicy()
dist = PythonDistribution(
    name = "instyper",
    config = python_config,
    packaging_policy = packaging_policy,
    files = ["src/instyper"],
    entry_point = "instyper:main"
)
register_target("default", dist)
