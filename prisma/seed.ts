import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';

const prisma = new PrismaClient();

async function seed() {
  try {
    console.log('Starting database seeding...');

    // Optional: Clear existing data
    // await clearDatabase();
    
    // Import counselling data from JSON file if it exists
    await importCounsellingData();
    
    console.log('Database seeding completed successfully!');
  } catch (error) {
    console.error('Error seeding database:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

async function clearDatabase() {
  console.log('Clearing existing data...');
  await prisma.counsellingData.deleteMany({});
  await prisma.processedFile.deleteMany({});
  console.log('Existing data cleared.');
}

async function importCounsellingData() {
  const jsonPath = path.join(process.cwd(), 'data', 'counselling_data.json');
  
  if (fs.existsSync(jsonPath)) {
    console.log(`Importing counselling data from ${jsonPath}...`);
    
    const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
    
    if (!Array.isArray(data)) {
      throw new Error('Expected counselling_data.json to contain an array');
    }
    
    console.log(`Found ${data.length} records to import`);
    
    // Split into batches to avoid overwhelming the database
    const batchSize = 100;
    let imported = 0;
    
    for (let i = 0; i < data.length; i += batchSize) {
      const batch = data.slice(i, i + batchSize);
      
      const records = batch.map(item => ({
        year: item.year || 2024,
        round: item.round || 1,
        rank: item.cutoffRank || item.lastRank,
        quota: item.quota,
        state: item.state,
        collegeName: item.college || item.college_name,
        course: item.course,
        category: item.category,
        subCategory: null,
        gender: null,
        physicallyHandicapped: null,
        marksObtained: null,
        maxMarks: null,
        status: null,
        dateOfAdmission: null,
      }));
      
      await prisma.counsellingData.createMany({
        data: records,
        skipDuplicates: true,
      });
      
      imported += batch.length;
      console.log(`Imported ${imported}/${data.length} records...`);
    }
    
    console.log('Counselling data import completed!');
  } else {
    console.log(`No counselling data found at ${jsonPath}, skipping import.`);
  }
}

// Run the seeding function
seed()
  .then(() => {
    console.log('Seeding completed successfully!');
    process.exit(0);
  })
  .catch(e => {
    console.error('Error during seeding:', e);
    process.exit(1);
  });
