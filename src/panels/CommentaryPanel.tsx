export function CommentaryPanel() {
  const steps = [
    { step_number: 1, title: 'Venue Analysis', description: 'Analyze venue conditions' },
    { step_number: 2, title: 'Opponent Assessment', description: 'Evaluate opponent strengths' },
    { step_number: 3, title: 'Squad Optimization', description: 'Run ILP optimization' },
    { step_number: 4, title: 'Win Probability', description: 'Monte Carlo simulation' }
  ]

  return (
    <div className="panel" data-testid="commentary-panel">
      <h2>AI Commentary</h2>
      <div className="panel-content">
        <div data-testid="commentary-steps">
          {steps.map((step, index) => (
            <div key={step.step_number} data-testid={`step-${index}`}>
              <h4>Step {step.step_number}: {step.title}</h4>
              <p>{step.description}</p>
            </div>
          ))}
        </div>
        <div data-testid="total-steps">Total Commentary Steps: {steps.length}</div>
      </div>
    </div>
  )
}
