/**
 * Recon Client State Engine (modules/state.js)
 * Central store for current session, datasets, mapping proposals, and assessment results.
 */

export const ReconState = {
  sessionId: null,
  currentStep: 1,
  assessmentData: null,
  resultsData: null,
  adapterCode: "",
  activeContract: null,
  isLocked: false,
  subscribers: new Set(),

  setSession(id) {
    this.sessionId = id;
    this.notify("session", id);
  },

  setAssessment(data) {
    this.assessmentData = data;
    this.sessionId = data.session_id;
    this.notify("assessment", data);
  },

  setResults(results) {
    this.resultsData = results;
    this.notify("results", results);
  },

  setStep(step) {
    this.currentStep = step;
    this.notify("step", step);
  },

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  },

  notify(event, payload) {
    this.subscribers.forEach(cb => {
      try {
        cb(event, payload);
      } catch (err) {
        console.warn("[ReconState] Subscriber error:", err);
      }
    });
  },
};
