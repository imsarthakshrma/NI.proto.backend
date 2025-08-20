"""
ChromaDB Setup Script for Native IQ
Sets up ChromaDB for vector embeddings and semantic search
"""

import chromadb
import os
from dotenv import load_dotenv
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer

load_dotenv()

def setup_chromadb():
    """Set up ChromaDB for Native IQ vector storage"""
    
    persist_directory = os.getenv('CHROMADB_PERSIST_DIRECTORY', './data/chromadb')
    collection_name = os.getenv('CHROMADB_COLLECTION_NAME', 'native_iq_memory')
    
    try:
        print(f"🔄 Setting up ChromaDB at {persist_directory}")
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        client = chromadb.PersistentClient(path=persist_directory)
        
        # Create or get collection
        try:
            collection = client.create_collection(
                name=collection_name,
                metadata={"description": "Native IQ semantic memory storage"}
            )
            print(f"✅ Created new collection: {collection_name}")
        except Exception:
            collection = client.get_collection(name=collection_name)
            print(f"✅ Using existing collection: {collection_name}")
        
        # Test embedding model
        print("🔄 Testing sentence transformer model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Test data for Native IQ context
        test_documents = [
            "User scheduled a meeting with John for tomorrow at 2 PM",
            "Alice mentioned she needs help with project deadlines",
            "Bob asked about automating email reminders for team meetings",
            "Sarah discussed workflow optimization for client onboarding",
            "Team discussed quarterly planning and resource allocation"
        ]
        
        test_metadata = [
            {"type": "meeting", "user": "user1", "timestamp": "2025-08-19T14:00:00"},
            {"type": "task_request", "user": "alice", "timestamp": "2025-08-19T14:15:00"},
            {"type": "automation_inquiry", "user": "bob", "timestamp": "2025-08-19T14:30:00"},
            {"type": "process_discussion", "user": "sarah", "timestamp": "2025-08-19T14:45:00"},
            {"type": "strategic_planning", "user": "team", "timestamp": "2025-08-19T15:00:00"}
        ]
        
        # Generate embeddings
        embeddings = model.encode(test_documents).tolist()
        
        # Add test data to collection
        collection.add(
            documents=test_documents,
            embeddings=embeddings,
            metadatas=test_metadata,
            ids=[f"test_doc_{i}" for i in range(len(test_documents))]
        )
        
        print(f"✅ Added {len(test_documents)} test documents to collection")
        
        # Test semantic search
        query = "meeting scheduling and calendar management"
        query_embedding = model.encode([query]).tolist()
        
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=3
        )
        
        print("🔍 Semantic search test:")
        print(f"Query: '{query}'")
        print("Top results:")
        for i, (doc, distance) in enumerate(zip(results['documents'][0], results['distances'][0])):
            print(f"  {i+1}. {doc} (similarity: {1-distance:.3f})")
        
        # Test metadata filtering
        meeting_results = collection.query(
            query_embeddings=query_embedding,
            where={"type": "meeting"},
            n_results=2
        )
        
        print(f"\n🔍 Filtered search (type='meeting'): {len(meeting_results['documents'][0])} results")
        
        # Store Native IQ configuration
        config_doc = f"Native IQ system initialized on {datetime.now().isoformat()}"
        config_embedding = model.encode([config_doc]).tolist()
        
        collection.add(
            documents=[config_doc],
            embeddings=config_embedding,
            metadatas=[{"type": "system_config", "version": "0.1.0"}],
            ids=["native_iq_config"]
        )
        
        print("✅ ChromaDB setup complete!")
        print(f"Collection: {collection_name}")
        print(f"Total documents: {collection.count()}")
        print(f"Persist directory: {persist_directory}")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB setup failed: {e}")
        return False

def test_chromadb_operations():
    """Test ChromaDB operations for Native IQ use cases"""
    
    persist_directory = os.getenv('CHROMADB_PERSIST_DIRECTORY', './data/chromadb')
    collection_name = os.getenv('CHROMADB_COLLECTION_NAME', 'native_iq_memory')
    
    try:
        client = chromadb.PersistentClient(path=persist_directory)
        collection = client.get_collection(name=collection_name)
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        print("🧪 Testing Native IQ use cases...")
        
        # Test 1: Contact resolution
        contact_query = "find John's email address"
        contact_embedding = model.encode([contact_query]).tolist()
        
        contact_results = collection.query(
            query_embeddings=contact_embedding,
            n_results=2
        )
        
        print(f"\n1. Contact Resolution Test:")
        print(f"   Query: '{contact_query}'")
        print(f"   Results: {len(contact_results['documents'][0])}")
        
        # Test 2: Meeting context
        meeting_query = "upcoming meetings and scheduling"
        meeting_embedding = model.encode([meeting_query]).tolist()
        
        meeting_results = collection.query(
            query_embeddings=meeting_embedding,
            where={"type": "meeting"},
            n_results=3
        )
        
        print(f"\n2. Meeting Context Test:")
        print(f"   Query: '{meeting_query}'")
        print(f"   Meeting-specific results: {len(meeting_results['documents'][0])}")
        
        # Test 3: Automation opportunities
        automation_query = "workflow automation and process improvement"
        automation_embedding = model.encode([automation_query]).tolist()
        
        automation_results = collection.query(
            query_embeddings=automation_embedding,
            n_results=3
        )
        
        print(f"\n3. Automation Opportunity Test:")
        print(f"   Query: '{automation_query}'")
        for doc in automation_results['documents'][0]:
            print(f"   - {doc}")
        
        print("\n✅ All ChromaDB operations working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB operations test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Native IQ ChromaDB Setup")
    print("=" * 40)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create a .env file with your ChromaDB configuration")
        exit(1)
    
    # Setup ChromaDB
    if setup_chromadb():
        print("\n🧪 Running operations test...")
        if test_chromadb_operations():
            print("\n🎉 ChromaDB setup complete!")
            print("\nChromaDB is ready for:")
            print("• Semantic search of conversations and contexts")
            print("• Contact and relationship memory")
            print("• Pattern recognition for automation opportunities")
            print("• Business intelligence and insights")
            print("\nNext: Deploy your Native IQ application!")
        else:
            print("\n❌ ChromaDB operations test failed")
    else:
        print("\n❌ ChromaDB setup failed")
