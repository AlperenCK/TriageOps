"""Artifact listeleme testi."""

from devops_agent.ado.builds import BuildReader


class _ArtifactClient:
    def get(self, path, *, params=None, collection_scope=False, as_text=False):
        assert path.endswith("/artifacts")
        return {
            "value": [
                {
                    "name": "test-results",
                    "resource": {
                        "type": "PipelineArtifact",
                        "downloadUrl": "https://dev/azure/download/test-results",
                        "properties": {"artifactsize": "2048"},
                    },
                },
                {
                    "name": "drop",
                    "resource": {
                        "type": "Container",
                        "downloadUrl": "https://dev/azure/download/drop",
                        "properties": {},
                    },
                },
            ]
        }


def test_list_artifacts_normalizes_fields():
    reader = BuildReader(_ArtifactClient())

    arts = reader.list_artifacts(123)

    assert [a["name"] for a in arts] == ["test-results", "drop"]
    assert arts[0]["type"] == "PipelineArtifact"
    assert arts[0]["downloadUrl"].endswith("/test-results")
    assert arts[0]["size_bytes"] == "2048"
    # Boyut bilgisi yoksa None donmeli, hata vermemeli.
    assert arts[1]["size_bytes"] is None
