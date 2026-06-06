import { createRouter, createWebHashHistory } from 'vue-router';
import Home from '@/views/Home.vue';
import PortfolioImport from '@/views/PortfolioImport.vue';
import PortfolioDiagnosis from '@/views/PortfolioDiagnosis.vue';
import AssetCycle from '@/views/AssetCycle.vue';
import EmotionCorrection from '@/views/EmotionCorrection.vue';
import Education from '@/views/Education.vue';
import CourseDetail from '@/views/CourseDetail.vue';
import Traceability from '@/views/Traceability.vue';
import Compliance from '@/views/Compliance.vue';

const routes = [
  { path: '/', component: Home },
  { path: '/portfolio/import', component: PortfolioImport },
  { path: '/portfolio/diagnosis', component: PortfolioDiagnosis },
  { path: '/cycle', component: AssetCycle },
  { path: '/emotion', component: EmotionCorrection },
  { path: '/education', component: Education },
  { path: '/course/:id', component: CourseDetail },
  { path: '/trace/:requestId', component: Traceability },
  { path: '/compliance', component: Compliance },
];

export default createRouter({
  history: createWebHashHistory(),
  routes,
});
