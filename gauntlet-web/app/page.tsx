import Hero from "@/components/Hero";
import Playground from "@/components/Playground";
import Architecture from "@/components/Architecture";
import Benchmarks from "@/components/Benchmarks";
import Install from "@/components/Install";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main className="max-w-[800px] mx-auto px-6">
      <div className="pt-[160px]">
        <Hero />
      </div>
      <div className="pt-[120px]" id="playground">
        <Playground />
      </div>
      <div className="pt-[160px]">
        <Architecture />
      </div>
      <div className="pt-[160px]">
        <Benchmarks />
      </div>
      <div className="pt-[160px]">
        <Install />
      </div>
      <div className="pt-[80px]">
        <Footer />
      </div>
    </main>
  );
}
