import Hero from "@/components/Hero";
import Playground from "@/components/Playground";
import Architecture from "@/components/Architecture";
import Benchmarks from "@/components/Benchmarks";
import Install from "@/components/Install";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main className="max-w-[720px] mx-auto px-6">
      <div className="pt-[160px]">
        <Hero />
      </div>
      <div className="pt-[120px]">
        <Playground />
      </div>
      <div className="pt-[120px]">
        <Architecture />
      </div>
      <div className="pt-[120px]">
        <Benchmarks />
      </div>
      <div className="pt-[120px]">
        <Install />
      </div>
      <div className="pt-[120px]">
        <Footer />
      </div>
    </main>
  );
}
