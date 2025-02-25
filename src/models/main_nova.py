// ...existing code...

    def _initialize_redis(self):
        """Initialize Redis client with proper event loop handling."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.redis_client = ClimateCache()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.error(f"Redis initialization failed: {str(e)}")
            self.redis_client = None

    async def cleanup(self) -> None:
        """Cleanup resources."""
        cleanup_errors = []
        
        # Close Redis connection if it exists
        if hasattr(self, 'redis_client') and self.redis_client is not None and not getattr(self.redis_client, '_closed', False):
            try:
                # Create a new event loop specifically for cleanup if needed
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except Exception:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                await self.redis_client.close()
            except Exception as e:
                cleanup_errors.append(f"Redis cleanup error: {str(e)}")
                logger.error(f"Error closing Redis connection: {str(e)}")
            finally:
                self.redis_client = None

        # Shutdown Ray if initialized
        if ray.is_initialized():
            try:
                ray.shutdown()
            except Exception as e:
                cleanup_errors.append(f"Ray cleanup error: {str(e)}")
                logger.error(f"Error shutting down Ray: {str(e)}")
        
        if cleanup_errors:
            logger.error(f"Cleanup completed with errors: {', '.join(cleanup_errors)}")
        else:
            logger.info("Cleanup completed successfully")

async def _process_query_internal(
            self,
            query: str,
            language_name: str,
            run_manager=None
        ) -> Dict[str, Any]:
            """Internal method to process queries, called by QueryProcessingChain."""
            start_time = time.time()
            try:
                # Query normalization
                norm_query = await self.nova_model.query_normalizer(query.lower().strip(), language_name)
                language_code = self.get_language_code(language_name)
                
                # Check cache
                cache_key = f"{language_code}:{norm_query}"
                if self.redis_client and not getattr(self.redis_client, '_closed', False):
                    cached_result = await self.redis_client.get(cache_key)
                    if cached_result:
                        logger.info("📚 Found cached response...")
                        return {
                            "success": True,
                            "response": cached_result['response'],
                            "citations": cached_result['citations'],
                            "faithfulness_score": cached_result.get('faithfulness_score', 0.8),
                            "processing_time": time.time() - start_time,
                            "language_code": language_code
                        }

                # Process query through routing
                route_result = await self.router.route_query(
                    query=norm_query,
                    language_code=language_code,
                    language_name=language_name,
                    translation=self.nova_model.nova_translation
                )
                
                if not route_result['should_proceed']:
                    return {
                        "success": False,
                        "response": route_result['routing_info']['message'],
                        "citations": [],
                        "faithfulness_score": 0.0,
                        "processing_time": time.time() - start_time,
                        "language_code": language_code
                    }

                processed_query = route_result['processed_query']
                english_query = route_result['english_query']
                
                # Run guards and retrieval in parallel
                guard_task = self.process_input_guards(norm_query)
                retrieval_task = get_documents(norm_query, self.index, self.embed_model, self.cohere_client)
                
                guard_results, reranked_docs = await asyncio.gather(guard_task, retrieval_task)
                
                if not guard_results['passed']:
                    return {
                        "success": False,
                        "response": "Query failed content moderation checks",
                        "citations": [],
                        "faithfulness_score": 0.0,
                        "processing_time": time.time() - start_time,
                        "language_code": language_code
                    }

                # Generate response with citations
                response, citations = await nova_chat(processed_query, reranked_docs, self.nova_model)
                
                # Quality checks
                contexts = extract_contexts(reranked_docs, max_contexts=5)
                faithfulness_score = await check_hallucination(
                    question=english_query,
                    answer=response,
                    contexts=contexts,
                    cohere_api_key=self.COHERE_API_KEY
                )
                
                # Translation if needed
                if route_result['routing_info']['needs_translation']:
                    response = await self.nova_model.nova_translation(response, 'english', language_name)
                
                # Ensure we keep the citations even after translation
                result = {
                    "success": True,
                    "response": response,
                    "citations": citations,
                    "faithfulness_score": faithfulness_score,
                    "processing_time": time.time() - start_time,
                    "language_code": language_code
                }
                
                # Cache the result with citations
                if self.redis_client and not getattr(self.redis_client, '_closed', False):
                    try:
                        cache_key = f"{language_code}:{norm_query}"
                        await self.redis_client.set(cache_key, result)
                    except Exception as e:
                        logger.warning(f"Failed to cache result: {str(e)}")
                
                return result

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error in internal query processing: {error_msg}")
                return {
                    "success": False,
                    "response": error_msg,
                    "citations": [],
                    "faithfulness_score": 0.0,
                    "processing_time": time.time() - start_time,
                    "language_code": language_code if 'language_code' in locals() else None
                }

// ...existing code...