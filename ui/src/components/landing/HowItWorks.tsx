import { Search, BrainCircuit, ShieldCheck } from 'lucide-react';

export function HowItWorks() {
  const steps = [
    {
      id: 1,
      title: "1. Start Session",
      desc: "Provide any topic. Cognimap initializes a targeted LangGraph agent tailored to your input.",
      icon: <Search className="w-6 h-6 text-primary-400" />,
      delay: "100ms",
    },
    {
      id: 2,
      title: "2. AI Synthesis",
      desc: "Async workers construct a 'Knowledge Frontier' graph, scraping content and forming an optimal curriculum path.",
      icon: <BrainCircuit className="w-6 h-6 text-purple-400" />,
      delay: "300ms",
    },
    {
      id: 3,
      title: "3. Dynamic Evaluation",
      desc: "Take adaptive quizzes based on the current node. The system evaluates and unlocks the next optimal edge.",
      icon: <ShieldCheck className="w-6 h-6 text-green-400" />,
      delay: "500ms",
    }
  ];

  return (
    <section className="relative z-10 w-full max-w-6xl mx-auto px-4 py-24 border-t border-border">
      <div className="text-center mb-16 animate-fade-up">
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">How Cognimap Works</h2>
        <p className="text-gray-400 max-w-2xl mx-auto">
          We replaced static tables of contents with a living curriculum.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
        {/* Connector Line (Desktop only) */}
        <div className="hidden md:block absolute top-[44px] left-[15%] right-[15%] h-0.5 bg-surface-2 -z-10">
          <div className="absolute top-0 left-0 h-full w-[40%] bg-gradient-to-r from-primary-500/0 via-primary-500 to-purple-500/0 animate-[shimmer_3s_linear_infinite]" style={{ backgroundSize: '200% 100%' }} />
        </div>

        {steps.map((step) => (
          <div 
            key={step.id} 
            className="flex flex-col items-center text-center group animate-fade-up"
            style={{ animationDelay: step.delay }}
          >
            <div className="w-24 h-24 rounded-full bg-surface-2 border-2 border-border mb-6 flex items-center justify-center relative shadow-card transition-colors duration-300 group-hover:border-primary-500/40">
              <div className="absolute inset-2 rounded-full glass-panel border-none flex items-center justify-center">
                {step.icon}
              </div>
            </div>
            
            <h3 className="text-lg font-semibold text-white mb-3">{step.title}</h3>
            <p className="text-sm text-gray-400 leading-relaxed max-w-xs">{step.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
