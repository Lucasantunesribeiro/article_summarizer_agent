#!/usr/bin/env python3
"""
Example usage of Article Summarizer Agent
Demonstrates different ways to use the agent programmatically
"""

from config import config
from main import ArticleSummarizerAgent


def example_basic_usage():
    """Basic usage example"""
    print("🔥 Example 1: Basic Usage")
    print("-" * 40)

    # Initialize agent
    agent = ArticleSummarizerAgent()

    # Example URL (replace with a real news article URL)
    url = "https://www.bbc.com/news"  # Use a real article URL

    try:
        result = agent.run(url)

        if result["success"]:
            print("✅ Summary created successfully!")
            print(f"📊 Statistics: {result['statistics']}")
            print(f"📁 Files: {list(result['files_created'].keys())}")
            print(f"⏱️ Time: {result['execution_time']:.2f} seconds")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


def example_configuration():
    """Example of configuring the agent"""
    print("\n🔧 Example 2: Configuration")
    print("-" * 40)

    # Modify configuration
    original_method = config.summarization.method
    original_length = config.summarization.summary_length

    config.summarization.method = "extractive"
    config.summarization.summary_length = "short"

    print(f"✅ Changed method to: {config.summarization.method}")
    print(f"✅ Changed length to: {config.summarization.summary_length}")

    # Restore original settings
    config.summarization.method = original_method
    config.summarization.summary_length = original_length


def example_batch_processing():
    """Example of processing multiple URLs"""
    print("\n📦 Example 3: Batch Processing")
    print("-" * 40)

    # Example URLs (replace with real article URLs)
    urls = [
        "https://example1.com/article1",
        "https://example2.com/article2",
        "https://example3.com/article3",
    ]

    agent = ArticleSummarizerAgent()
    results = []

    for i, url in enumerate(urls, 1):
        print(f"Processing article {i}/{len(urls)}...")
        try:
            result = agent.run(url)
            results.append(
                {
                    "url": url,
                    "success": result["success"],
                    "summary_length": len(result.get("summary", "").split())
                    if result["success"]
                    else 0,
                }
            )
        except Exception as e:
            print(f"❌ Failed to process {url}: {str(e)}")
            results.append({"url": url, "success": False, "error": str(e)})

    # Summary of batch processing
    successful = sum(1 for r in results if r["success"])
    print(f"\n📊 Batch Results: {successful}/{len(urls)} successful")


def example_status_check():
    """Example of checking agent status"""
    print("\n📋 Example 4: Status Check")
    print("-" * 40)

    try:
        agent = ArticleSummarizerAgent()
        status = agent.get_status()

        print(f"🤖 Agent Version: {status['version']}")
        print(f"⚙️ Current Method: {status['config']['summarization_method']}")
        print(f"📏 Summary Length: {status['config']['summary_length']}")
        print(f"💾 Cache Enabled: {status['config']['cache_enabled']}")
        print(f"📁 Output Formats: {', '.join(status['config']['output_formats'])}")

        storage = status["storage_info"]
        print(
            f"💾 Storage: {storage.get('total_files', 0)} files, {storage.get('total_size_mb', 0):.2f} MB"
        )

    except Exception as e:
        print(f"❌ Error checking status: {str(e)}")


def main():
    """Run all examples"""
    print("🤖 Article Summarizer Agent - Usage Examples")
    print("=" * 60)

    try:
        # Run examples
        example_basic_usage()
        example_configuration()
        example_batch_processing()
        example_status_check()

        print("\n🎉 All examples completed!")
        print("\nTo run the agent:")
        print("• Interactive: python main.py --interactive")
        print("• Direct: python main.py --url 'https://article-url.com'")
        print("• Help: python main.py --help")

    except Exception as e:
        print(f"❌ Examples failed: {str(e)}")
        print("Make sure to run 'python setup.py' first!")


if __name__ == "__main__":
    main()
