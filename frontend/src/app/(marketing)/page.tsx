import Navbar from "@/components/landing/Navbar";
import Hero from "@/components/landing/Hero";
import ProductPreview from "@/components/landing/ProductPreview";
import FeatureGrid from "@/components/landing/FeatureGrid";
import CTA from "@/components/landing/CTA";

export default function MarketingPage() {
  return (
    <main className="min-h-screen overflow-x-hidden bg-[#08090D] text-white">
      <Navbar />
      <Hero />
      <ProductPreview />
      <FeatureGrid />
      <CTA />
    </main>
  );
}
