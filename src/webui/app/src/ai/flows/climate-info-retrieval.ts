'use server';
/**
 * @fileOverview Climate change information retrieval AI agent.
 *
 * - climateInfoRetrieval - A function that handles climate change question answering.
 * - ClimateInfoRetrievalInput - The input type for the climateInfoRetrieval function.
 * - ClimateInfoRetrievalOutput - The return type for the climateInfoRetrieval function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const ClimateInfoRetrievalInputSchema = z.object({
  query: z.string().describe('The user query about climate change.'),
});
export type ClimateInfoRetrievalInput = z.infer<typeof ClimateInfoRetrievalInputSchema>;

const ClimateInfoRetrievalOutputSchema = z.object({
  answer: z.string().describe('The answer to the user query.'),
  resources: z.string().describe('Links to local resources related to climate change.'),
});
export type ClimateInfoRetrievalOutput = z.infer<typeof ClimateInfoRetrievalOutputSchema>;

export async function climateInfoRetrieval(input: ClimateInfoRetrievalInput): Promise<ClimateInfoRetrievalOutput> {
  return climateInfoRetrievalFlow(input);
}

const prompt = ai.definePrompt({
  name: 'climateInfoRetrievalPrompt',
  input: {schema: ClimateInfoRetrievalInputSchema},
  output: {schema: ClimateInfoRetrievalOutputSchema},
  prompt: `You are a climate change expert providing information and resources to users.

  Answer the user's question about climate change and provide links to local resources when available.

  Question: {{{query}}}
  `, 
});

const climateInfoRetrievalFlow = ai.defineFlow(
  {
    name: 'climateInfoRetrievalFlow',
    inputSchema: ClimateInfoRetrievalInputSchema,
    outputSchema: ClimateInfoRetrievalOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
