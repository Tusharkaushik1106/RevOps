class NotImplementedModel:
    def predict(self, features): raise NotImplementedError("ML model is deferred beyond Phase 0")
    def detect(self, records): raise NotImplementedError("Detector is deferred beyond Phase 0")
    def estimate(self, records): raise NotImplementedError("Estimator is deferred beyond Phase 0")
